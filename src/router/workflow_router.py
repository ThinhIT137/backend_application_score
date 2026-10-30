"""Explicit score approval, official result import, publication and delivery.
No prediction or dossier approval is treated as an admission decision.
"""
import csv
import hashlib
import io
import math
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import CurrentUser, require_admin
from src.core import security
from src.core.exceptions import DuLieuKhongHopLe, HoSoNotFound, TrangThaiKhongHopLe
from src.models.ho_so import NguyenVongSinhVien
from src.models.diem_thi_sinh import BangDiem, ChungChi
from src.models.admission import ToHopXetTuyen
from src.models.tham_chieu import ThiSinh, DanhMucMonHoc
from src.models.diem_chuan import LichSuDiemChuan, DiemTrungTuyen
from src.models.trang_thai_ho_so import TrangThaiDuyet, TrangThaiHoSo
from src.models.workflow import NotificationOutbox, ScoreImportLog
from src.repositories.diem_repository import DiemRepository
from src.schemas.diem_schema import DiemMonThpt
from src.services.conversion_service import convert_to_thpt
from src.services.result_state import result_label
from src.services.adapters.email_sender import SmtpEmailSender
from src.services.notification_service import NotificationService

# API dành cho cán bộ chốt điểm/kết quả, nhập CSV và gửi thông báo. Dự báo AI không phải kết quả chính thức.
router = APIRouter(prefix="/xet-tuyen", tags=["admission-workflow"])


# Dữ liệu chốt điểm phải có căn cứ source; có thể chọn bảng điểm, chứng chỉ hoặc điểm đã đối soát.
class ScoreApproval(BaseModel):
    kind: Literal["transcript", "hoc_ba", "hsa", "tsa", "manual", "exempt"]
    transcript_ids: list[str] = Field(default_factory=list, max_length=10)
    certificate_id: str | None = None
    manual_score: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    priority: float = Field(default=0, ge=0, le=10, allow_inf_nan=False)
    scale_max: float = Field(default=30, gt=0, le=10000, allow_inf_nan=False)
    source: str = Field(min_length=5, max_length=2000)


def dossier(db, key, lock=True):
    query = select(NguyenVongSinhVien).where(NguyenVongSinhVien.ma_ho_so == key)
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise HoSoNotFound("Không tìm thấy hồ sơ")
    if lock:
        from src.models.submission_operation import SubmissionOperation
        if db.scalar(select(SubmissionOperation.operation_id).where(
                SubmissionOperation.dossier_id == key, SubmissionOperation.status != "completed")):
            raise TrangThaiKhongHopLe("Hồ sơ đang lưu minh chứng")
    return row


# Kết quả đã công bố bị khóa, không cho ghi đè qua các thao tác xét tuyển bên dưới.
def editable(row):
    if row.cong_bo_at:
        raise TrangThaiKhongHopLe("Kết quả đã công bố, không được ghi đè")


# Chỉ chuyển hồ sơ hợp lệ sang đang xử lý; duyệt hồ sơ chưa đồng nghĩa thí sinh đã đỗ.
@router.patch("/{key}/bat-dau-xu-ly")
def start_processing(key: str, admin: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    row = dossier(db, key)
    editable(row)
    if row.trang_thai != TrangThaiHoSo.hop_le:
        raise TrangThaiKhongHopLe("Chỉ hồ sơ hợp lệ mới được bắt đầu xét tuyển")
    row.trang_thai = TrangThaiHoSo.dang_xu_ly
    row.ma_admin_xu_ly = admin.ma_admin
    db.flush()
    return {"ma_ho_so": key, "trang_thai": row.trang_thai}


# Chốt điểm ở trạng thái đang xử lý và lưu dấu tính toán để cán bộ đối soát về sau.
@router.post("/{key}/chot-diem")
def approve_score(key: str, payload: ScoreApproval, admin: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    row = dossier(db, key)
    editable(row)
    if row.trang_thai != TrangThaiHoSo.dang_xu_ly:
        raise DuLieuKhongHopLe("Chỉ chốt điểm khi hồ sơ đang xét tuyển")
    subjects = {}
    if payload.kind in {"transcript", "hoc_ba"}:
        if not payload.transcript_ids or len(set(payload.transcript_ids)) != len(payload.transcript_ids):
            raise DuLieuKhongHopLe("Chọn bảng điểm không trùng; nhiều bảng được lấy trung bình từng môn")
        combination = db.get(ToHopXetTuyen, row.ma_to_hop) if row.ma_to_hop else None
        codes = [getattr(combination, f"ma_mon_{i}", None) for i in (1, 2, 3)]
        if not all(codes) or len(set(codes)) != 3:
            raise DuLieuKhongHopLe("Tổ hợp chưa có đủ ba mã môn khác nhau")
        # Với nhiều bảng điểm được chọn, lấy trung bình từng môn trong tổ hợp rồi cộng ba môn.
        totals = {code: [] for code in codes}
        for transcript_id in payload.transcript_ids:
            transcript = db.get(BangDiem, transcript_id)
            if not transcript or transcript.cccd != row.cccd:
                raise DuLieuKhongHopLe("Bảng điểm không thuộc thí sinh")
            values = {g.ma_mon: g.diem_so for g in transcript.chi_tiet}
            for code in codes:
                value = values.get(code)
                if value is None or not math.isfinite(value) or not 0 <= value <= 10:
                    raise DuLieuKhongHopLe(f"Thiếu/không hợp lệ điểm môn {code}")
                totals[code].append(value)
        subjects = {code: sum(values) / len(values) for code, values in totals.items()}
        base = sum(subjects.values())
        if payload.kind == "hoc_ba":
            base = convert_to_thpt("hoc_ba", base, row.nam_tuyen_sinh)
    elif payload.kind in {"hsa", "tsa"}:
        cert = db.get(ChungChi, payload.certificate_id) if payload.certificate_id else None
        if not cert or cert.cccd != row.cccd or cert.trang_thai_duyet != TrangThaiDuyet.hop_le:
            raise DuLieuKhongHopLe("Chọn chứng chỉ điểm đã được xác minh của thí sinh")
        try:
            base = convert_to_thpt(payload.kind, float(cert.diem_hoac_hang), row.nam_tuyen_sinh)
        except (ValueError, TypeError):
            raise DuLieuKhongHopLe("Điểm chứng chỉ không hợp lệ")
    elif payload.kind == "manual":
        if payload.manual_score is None:
            raise DuLieuKhongHopLe("Nhập điểm đã đối soát kèm căn cứ quy đổi")
        base = payload.manual_score
    else:
        base = None
        if payload.priority:
            raise DuLieuKhongHopLe("Hồ sơ miễn điểm không cộng điểm ưu tiên")
    total = None if base is None else round(base + payload.priority, 4)
    if total is not None and total > payload.scale_max:
        raise DuLieuKhongHopLe("Tổng điểm vượt thang điểm đã chọn; kiểm tra lại ưu tiên/quy đổi")
    row.tong_diem_xet_tuyen = total
    row.diem_uu_tien_ap_dung = payload.priority
    # Lưu nguồn, đầu vào, điểm gốc/ưu tiên/tổng và người chốt; chưa quyết định đỗ/trượt ở bước này.
    row.diem_trace = {**payload.model_dump(), "subjects": subjects, "base": base, "total": total,
        "admin": admin.ma_admin, "approved_at": datetime.now().isoformat()}
    row.trang_thai = TrangThaiHoSo.dang_xu_ly
    row.chot_ket_qua_at = None
    row.nguon_ket_qua = None
    db.flush()
    return {"ma_ho_so": key, "tong_diem_xet_tuyen": total, "diem_trace": row.diem_trace}


class Decision(BaseModel):
    ma_ho_so: str
    result: Literal["trung_tuyen", "khong_trung_tuyen"]
    exception_reason: str | None = Field(default=None, max_length=2000)


class Decisions(BaseModel):
    source: str = Field(min_length=5, max_length=2000)
    rows: list[Decision] = Field(min_length=1, max_length=1000)


# Nhận danh sách quyết định chính thức; kiểm tra điều kiện, chỉ tiêu và mỗi người chỉ đỗ một nguyện vọng/mùa.
@router.post("/chot-ket-qua")
def approve_decisions(payload: Decisions, admin: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    ids = [item.ma_ho_so for item in payload.rows]
    if len(ids) != len(set(ids)):
        raise DuLieuKhongHopLe("Danh sách bị trùng mã hồ sơ")
    # Khóa theo thứ tự ổn định để phối hợp các yêu cầu chốt đồng thời; đây không phải bước tự xếp hạng.
    rows = [dossier(db, key) for key in sorted(ids)]
    indexed = {row.ma_ho_so: row for row in rows}
    for cccd in sorted({r.cccd for r in rows}):
        db.scalar(select(ThiSinh).where(ThiSinh.cccd == cccd).with_for_update())
    # Serialize all decisions for the affected program/year against the quota rows.
    for program, year in sorted({(r.ma_chuong_trinh, r.nam_tuyen_sinh) for r in rows}):
        db.scalar(select(LichSuDiemChuan).where(LichSuDiemChuan.ma_chuong_trinh == program, LichSuDiemChuan.nam == year).with_for_update())
    for item in payload.rows:
        row = indexed[item.ma_ho_so]
        editable(row)
        if row.trang_thai != TrangThaiHoSo.dang_xu_ly:
            raise DuLieuKhongHopLe("Còn hồ sơ chưa kiểm tra hợp lệ")
        if item.result == "trung_tuyen":
            if row.trang_thai != TrangThaiHoSo.dang_xu_ly or not row.diem_trace:
                raise DuLieuKhongHopLe("Trúng tuyển cần hồ sơ hợp lệ và điểm/miễn điểm đã chốt")
            cutoff = db.scalar(select(DiemTrungTuyen).join(LichSuDiemChuan).where(
                LichSuDiemChuan.ma_chuong_trinh == row.ma_chuong_trinh, LichSuDiemChuan.nam == row.nam_tuyen_sinh,
                DiemTrungTuyen.ma_phuong_thuc == row.ma_phuong_thuc))
            reason = (item.exception_reason or "").strip()
            if cutoff and not reason:
                if cutoff.diem > 0 and (row.tong_diem_xet_tuyen is None or row.tong_diem_xet_tuyen < cutoff.diem):
                    raise DuLieuKhongHopLe("Chưa đạt điểm chuẩn; ngoại lệ cần ghi căn cứ được duyệt")
                if cutoff.nguyen_vong_toi_da and row.nguyen_vong > cutoff.nguyen_vong_toi_da:
                    raise DuLieuKhongHopLe("Vượt giới hạn nguyện vọng")
                if cutoff.diem_uu_tien_toi_thieu is not None and (row.diem_uu_tien_ap_dung or 0) < cutoff.diem_uu_tien_toi_thieu:
                    raise DuLieuKhongHopLe("Chưa đạt điều kiện điểm ưu tiên")
                if cutoff.dieu_kien_mon:
                    for code, minimum in cutoff.dieu_kien_mon.items():
                        if not isinstance(minimum, (int, float)) or code not in row.diem_trace.get("subjects", {}):
                            raise DuLieuKhongHopLe("Điều kiện môn cần đối soát thủ công và ghi căn cứ ngoại lệ")
                        if row.diem_trace["subjects"][code] < minimum:
                            raise DuLieuKhongHopLe(f"Chưa đạt điều kiện môn {code}")
            if row.diem_trace.get("kind") == "exempt" and not reason:
                raise DuLieuKhongHopLe("Trúng tuyển miễn điểm cần ghi căn cứ xét tuyển thẳng")
        row.trang_thai = TrangThaiHoSo.do if item.result == "trung_tuyen" else TrangThaiHoSo.truot
        row.nguon_ket_qua = f"{payload.source}\nNgười chốt: {admin.ma_admin}" + (f"\nNgoại lệ: {item.exception_reason}" if item.exception_reason else "")
        row.chot_ket_qua_at = datetime.now()
    # Đẩy thay đổi vào transaction để đếm cả quyết định mới; nếu vượt chỉ tiêu thì báo lỗi và rollback.

    db.flush()
    for program, year in {(r.ma_chuong_trinh, r.nam_tuyen_sinh) for r in rows}:
        admitted = list(db.scalars(select(NguyenVongSinhVien).where(NguyenVongSinhVien.nam_tuyen_sinh == year, NguyenVongSinhVien.trang_thai == TrangThaiHoSo.do)))
        people = [r.cccd for r in admitted]
        if len(people) != len(set(people)):
            raise DuLieuKhongHopLe("Một thí sinh chỉ được trúng tuyển một nguyện vọng trong cùng mùa")
        quota = db.scalar(select(LichSuDiemChuan).where(LichSuDiemChuan.ma_chuong_trinh == program, LichSuDiemChuan.nam == year))
        count = sum(r.ma_chuong_trinh == program for r in admitted)
        if count and (not quota or count > quota.chi_tieu):
            raise DuLieuKhongHopLe("Danh sách vượt chỉ tiêu hoặc chưa thiết lập chỉ tiêu")
    return {"updated": len(rows)}


@router.get("/xem-truoc/{year}")
def preview(year: int, admin: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(NguyenVongSinhVien).where(NguyenVongSinhVien.nam_tuyen_sinh == year)).all()
    return [{"ma_ho_so": r.ma_ho_so, "cccd": r.cccd, "ma_chuong_trinh": r.ma_chuong_trinh,
        "trang_thai": r.trang_thai, "diem": r.tong_diem_xet_tuyen, "diem_da_chot": bool(r.diem_trace),
        "ket_qua_du_kien": r.trang_thai.value, "ket_qua": result_label(r), "nguon": r.nguon_ket_qua} for r in rows]


class ImportScores(BaseModel):
    year: int = Field(ge=2000, le=2100)
    source: str = Field(min_length=5, max_length=2000)
    csv_text: str = Field(min_length=1, max_length=2000000)
    commit: bool = False


# CSV có bước xem trước; chỉ commit khi toàn bộ dữ liệu hợp lệ, digest ngăn nhập lại cùng nội dung/nguồn/năm.
@router.post("/nhap-diem-thpt")
def import_scores(payload: ImportScores, admin: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    reader = csv.DictReader(io.StringIO(payload.csv_text.lstrip("\ufeff")))
    headers = reader.fieldnames or []
    if "cccd" not in headers or len(headers) != len(set(headers)):
        raise DuLieuKhongHopLe("CSV cần cột cccd và các cột mã môn không trùng")
    codes = [code for code in headers if code != "cccd"]
    if not codes or any(db.get(DanhMucMonHoc, code) is None for code in codes):
        raise DuLieuKhongHopLe("Mã môn trong CSV không tồn tại")
    records, errors, seen = [], [], set()
    for line, raw in enumerate(reader, 2):
        if line > 10001:
            raise DuLieuKhongHopLe("Mỗi lần nhập tối đa 10.000 dòng")
        cccd = (raw.get("cccd") or "").strip()
        try:
            if cccd in seen or db.get(ThiSinh, cccd) is None:
                raise ValueError("CCCD trùng hoặc không tồn tại")
            seen.add(cccd)
            values = [DiemMonThpt(ma_mon=code, diem_so=float(raw[code])) for code in codes if raw.get(code, "").strip()]
            if not values:
                raise ValueError("Không có điểm môn")
            records.append((cccd, values))
        except (ValueError, TypeError) as exc:
            errors.append({"line": line, "cccd": cccd, "error": str(exc)[:300]})
    digest = hashlib.sha256(f"{payload.year}\n{payload.source}\n{payload.csv_text}".encode()).hexdigest()
    duplicate = db.get(ScoreImportLog, digest) is not None
    if payload.commit:
        if errors or not records:
            raise DuLieuKhongHopLe("CSV còn lỗi hoặc rỗng; chưa ghi bất kỳ dòng nào")
        if not duplicate:
            repo = DiemRepository(db)
            for cccd, values in records:
                repo.upsert_bang_diem_tnthpt(cccd, payload.year, values)
            db.add(ScoreImportLog(digest=digest, source=payload.source, year=payload.year, admin_id=admin.ma_admin, row_count=len(records)))
            db.flush()
    return {"valid": len(records), "errors": errors, "committed": payload.commit and not errors, "duplicate": duplicate, "digest": digest, "source": payload.source}


# Đọc trạng thái outbox để biết đã gửi, đang chờ hay lỗi; có bản ghi không đồng nghĩa email đã tới người nhận.
@router.get("/thong-bao/{year}")
def delivery_status(year: int, admin: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    return [{"ma_ho_so": n.ma_ho_so, "email": n.email, "status": n.status, "attempts": n.attempts, "error": n.error, "sent_at": n.sent_at}
        for n in db.scalars(select(NotificationOutbox).join(NguyenVongSinhVien).where(NguyenVongSinhVien.nam_tuyen_sinh == year))]


# Nhận tối đa 100 thông báo chưa gửi; đánh dấu nhận việc trước SMTP để worker khác không lấy trùng.
@router.post("/gui-thong-bao/{year}")
def deliver(year: int, admin: CurrentUser = Depends(require_admin), db: Session = Depends(get_db)):
    settings = security.get_settings()
    if settings.email_provider != "smtp" or not settings.smtp_host or not settings.smtp_from:
        raise DuLieuKhongHopLe("Chưa cấu hình SMTP thật; không đánh dấu đã gửi")
    jobs = list(db.scalars(select(NotificationOutbox).join(NguyenVongSinhVien).where(
        NguyenVongSinhVien.nam_tuyen_sinh == year, NotificationOutbox.status.in_(["pending", "failed", "missing_email"])
    ).with_for_update(skip_locked=True).limit(100)))
    ids = [job.ma_ho_so for job in jobs]
    for job in jobs:
        job.status = "sending"
        job.attempts += 1
    db.commit()  # Claim before SMTP; a second worker cannot claim these jobs.
    sender = SmtpEmailSender(host=settings.smtp_host, port=settings.smtp_port, username=settings.smtp_username,
        password=settings.smtp_password, use_tls=settings.smtp_use_tls, from_addr=settings.smtp_from)
    sent = 0
    for key in ids:
        job, row = db.get(NotificationOutbox, key), dossier(db, key, False)
        student = db.get(ThiSinh, row.cccd)
        job.email = student.email if student else None
        if not job.email:
            job.status, job.error = "missing_email", "Thí sinh chưa cung cấp email"
        else:
            try:
                sender.send(job.email, NotificationService.build_subject(row), NotificationService.build_body(row))
                job.status, job.sent_at, job.error = "sent", datetime.now(), None
                sent += 1
            except Exception:
                job.status, job.error = "failed", "SMTP gửi thất bại; có thể thử lại"
        db.commit()
    return {"processed": len(ids), "sent": sent}

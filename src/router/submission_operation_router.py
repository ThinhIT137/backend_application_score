"""Giao dịch bù: ghi dữ liệu trước, lưu file sau, không giữ khóa DB khi gọi Storage."""
import hashlib
import json
import time
from copy import deepcopy
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from jose import jwt, JWTError
from pydantic import Field, ValidationError
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.config import get_settings
from src.core.security import CurrentUser, require_thi_sinh
from src.core.exceptions import ForbiddenError, HoSoNotFound, TrangThaiKhongHopLe
from src.models.submission_operation import SubmissionOperation
from src.models.tham_chieu import ThiSinh
from src.models.ho_so import NguyenVongSinhVien
from src.models.diem_thi_sinh import BangDiem, DiemChiTiet, ChungChi
from src.models.giai_thuong import GiaiThuong
from src.models.trang_thai_ho_so import TrangThaiDuyet
from src.schemas.admission_schema import InputModel, Submission
from src.router.candidate_auth_router import Profile
from src.services.admission_service import AdmissionService
from src.services.candidate_preferences_service import pending_self_submission
from src.models.workflow import NotificationOutbox

router = APIRouter(prefix="/submission-operations", tags=["submission-operations"])


class OperationInput(InputModel):
    operation_id: str
    document: str = Field(max_length=300000)
    proof: str
    run_id: str


class OperationDocument(InputModel):
    submission: Submission
    profile: Profile
    files: list[dict] = Field(default_factory=list, max_length=30)


class Command(InputModel):
    proof: str
    run_id: str


def digest(value):
    # Chuỗi chuẩn do Next ký; chỉ chứa hash, không ghi mật khẩu/token vào nhật ký.
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def receipt(proof, operation_id, cccd, action, payload_hash=None, run_id=None):
    try:
        claims = jwt.decode(proof, get_settings().jwt_secret, algorithms=["HS256"],
                            audience="submission-coordinator", options={"require_exp": True})
        if (claims.get("purpose") != "submission-coordinator" or claims.get("sub") != cccd
                or claims.get("operation_id") != operation_id or claims.get("action") != action
                or (run_id is not None and claims.get("run_id") != run_id)
                or (payload_hash is not None and claims.get("payload_hash") != payload_hash)):
            raise ValueError()
    except (JWTError, ValueError):
        raise ForbiddenError("Yêu cầu điều phối hồ sơ không hợp lệ")


def locked(db, operation_id, user):
    candidate = db.scalar(select(ThiSinh).where(ThiSinh.cccd == user.cccd).with_for_update())
    if candidate is None:
        raise HoSoNotFound("Không tìm thấy thí sinh")
    op = db.scalar(select(SubmissionOperation).where(SubmissionOperation.operation_id == operation_id).with_for_update())
    if op is None:
        raise HoSoNotFound("Không tìm thấy lần nộp")
    if op.cccd != user.cccd:
        raise ForbiddenError("Lần nộp không thuộc tài khoản")
    return candidate, op


def output(op):
    return {"operation_id": op.operation_id, "status": op.status, "ma_ho_so": op.dossier_id,
            "files": op.journal["files"], "payload_hash": op.payload_hash}


def committed_output(db, op):
    # FastAPI có thể chạy phần kết thúc yield-dependency SAU khi gửi response.
    # Phải commit ngay ở handler trước khi Next được phép upload/xóa file.
    # Chụp dữ liệu trả về trước commit để không lazy-load ORM đã expire sau commit.
    result = deepcopy(output(op))
    db.commit()
    return result


def row_state(row):
    """Ảnh chụp toàn bộ cột của dữ liệu mới; không bao gồm tài khoản/mật khẩu."""
    def encode(value):
        if isinstance(value, datetime):
            return value.isoformat()
        return value.value if hasattr(value, "value") else value
    return {column.key: encode(getattr(row, column.key)) for column in row.__table__.columns}


def child_state(db, journal, cccd):
    # Khóa đúng các dòng do lần nộp tạo. Mất/thêm/sửa điểm, chủ sở hữu hoặc trạng thái đều làm lệch snapshot.
    state = {}
    for name, model, primary in (("transcripts", BangDiem, BangDiem.ma_bang_diem),
            ("certificates", ChungChi, ChungChi.ma_chung_chi),
            ("awards", GiaiThuong, GiaiThuong.ma_giai_thuong)):
        rows = db.scalars(select(model).where(primary.in_(journal[name])).order_by(primary)
                          .with_for_update().execution_options(populate_existing=True)).all()
        state[name] = [row_state(row) for row in rows]
    details = db.scalars(select(DiemChiTiet).where(DiemChiTiet.ma_bang_diem.in_(journal["transcripts"]))
        .order_by(DiemChiTiet.ma_chi_tiet).with_for_update().execution_options(populate_existing=True)).all()
    state["details"] = [row_state(row) for row in details]
    return state


def require_unchanged(db, op, candidate):
    journal = op.journal
    if child_state(db, journal, op.cccd) != journal.get("children_snapshot"):
        raise TrangThaiKhongHopLe("Dữ liệu minh chứng đã thay đổi hoặc được xác minh, cần cán bộ đối soát")
    if db.scalar(select(NotificationOutbox.ma_ho_so).where(NotificationOutbox.ma_ho_so == op.dossier_id).with_for_update()):
        raise TrangThaiKhongHopLe("Hồ sơ đã có thông báo, không thể hoàn tác")
    if any(getattr(candidate, field) != value for field, value in journal["profile_after"].items()):
        raise TrangThaiKhongHopLe("Thông tin thí sinh đã thay đổi, cần đối soát trước khi hoàn tác")


@router.post("")
def create(payload: OperationInput, user: CurrentUser = Depends(require_thi_sinh), db: Session = Depends(get_db)):
    try:
        operation_id = str(UUID(payload.operation_id))
    except ValueError:
        raise HTTPException(status_code=422, detail="Mã lần nộp không hợp lệ")
    payload_hash = hashlib.sha256(payload.document.encode()).hexdigest()
    receipt(payload.proof, operation_id, user.cccd, "create", payload_hash, payload.run_id)
    run_id = payload.run_id
    try:
        payload = OperationDocument.model_validate_json(payload.document)
    except ValidationError:
        raise HTTPException(status_code=422, detail="Dữ liệu hồ sơ không hợp lệ")
    candidate = db.scalar(select(ThiSinh).where(ThiSinh.cccd == user.cccd).with_for_update())
    if candidate is None:
        raise HoSoNotFound("Không tìm thấy thí sinh")
    previous = db.get(SubmissionOperation, operation_id)
    if previous:
        if previous.cccd != user.cccd or previous.payload_hash != payload_hash:
            raise TrangThaiKhongHopLe("Mã lần nộp đã được sử dụng")
        if previous.status in ("pending", "aborting", "cleanup_pending"):
            if previous.journal.get("lease_until", 0) > time.time():
                raise TrangThaiKhongHopLe("Lần nộp đang được xử lý. Vui lòng đợi rồi thử lại")
            previous.journal = {**previous.journal, "run_id": run_id, "lease_until": time.time() + 300}
            db.flush()
        return committed_output(db, previous)
    if db.scalar(select(SubmissionOperation.operation_id).where(SubmissionOperation.cccd == user.cccd,
            SubmissionOperation.status.in_(["pending", "aborting", "cleanup_pending", "withdraw_cleanup"]))):
        raise TrangThaiKhongHopLe("Cần hoàn tất hoặc hoàn tác lần nộp trước")
    keys = [f.get("key") for f in payload.files]
    if len(set(keys)) != len(keys):
        raise TrangThaiKhongHopLe("Minh chứng trùng")
    references = {item.file_dinh_kem for item in [*payload.submission.chung_chi, *payload.submission.giai_thuong]}
    for item in payload.files:
        key = item.get("key", "")
        if key not in references or not key.startswith(f"{user.cccd}/") or len(item.get("sha256", "")) != 64:
            raise ForbiddenError("Minh chứng chưa được gắn vào hồ sơ")
    journal = {"files": payload.files, "run_id": run_id, "lease_until": time.time() + 300,
        "profile_before": {k: getattr(candidate, k) for k in type(payload.profile).model_fields},
        "profile_after": payload.profile.model_dump()}
    for field, value in payload.profile.model_dump().items():
        setattr(candidate, field, value)
    AdmissionService(db).submit(payload.submission, user, journal)
    journal["children_snapshot"] = child_state(db, journal, user.cccd)
    op = SubmissionOperation(operation_id=operation_id, cccd=user.cccd, status="pending",
        dossier_id=journal["dossier"], payload_hash=payload_hash, journal=journal, created_at=datetime.now())
    db.add(op)
    db.flush()
    return committed_output(db, op)


@router.get("/{operation_id}")
def get(operation_id: str, user: CurrentUser = Depends(require_thi_sinh), db: Session = Depends(get_db)):
    return output(locked(db, operation_id, user)[1])


@router.post("/{operation_id}/{action}")
def command(operation_id: str, action: str, payload: Command,
            user: CurrentUser = Depends(require_thi_sinh), db: Session = Depends(get_db)):
    receipt(payload.proof, operation_id, user.cccd, action, run_id=payload.run_id)
    candidate, op = locked(db, operation_id, user)
    if op.status not in ("completed", "rolled_back") and op.journal.get("run_id") != payload.run_id:
        raise TrangThaiKhongHopLe("Lần xử lý đã thay đổi")
    if action == "finalize":
        if op.status not in ("pending", "completed"):
            raise TrangThaiKhongHopLe("Lần nộp đang được hoàn tác")
        op.status = "completed"
    elif action == "cleanup-complete":
        if op.status == "rolled_back":
            return committed_output(db, op)
        if op.status != "cleanup_pending" or not op.journal.get("data_rolled_back"):
            raise TrangThaiKhongHopLe("Chưa hoàn tác dữ liệu")
        op.status = "rolled_back"
    elif action in ("abort", "compensate"):
        if op.status == "completed":
            raise TrangThaiKhongHopLe("Hồ sơ đã hoàn tất, không hoàn tác bằng luồng upload")
        if op.status == "rolled_back":
            return committed_output(db, op)
        if op.status == "cleanup_pending" and op.journal.get("data_rolled_back"):
            return committed_output(db, op)
        row = db.scalar(select(NguyenVongSinhVien).where(NguyenVongSinhVien.ma_ho_so == op.dossier_id).with_for_update())
        if row is None or row.cccd != user.cccd or not pending_self_submission(row):
            raise TrangThaiKhongHopLe("Hồ sơ đã thay đổi, cần cán bộ đối soát")
        require_unchanged(db, op, candidate)
        if action == "abort":
            op.status = "aborting"
        else:
            if op.status != "aborting":
                raise TrangThaiKhongHopLe("Phải dọn file trước khi hoàn tác dữ liệu")
            journal = op.journal
            # Xóa đúng ID được tạo trong transaction, giữ nguyên bảng điểm/chứng chỉ cũ.
            db.execute(delete(DiemChiTiet).where(DiemChiTiet.ma_bang_diem.in_(journal["transcripts"])))
            db.execute(delete(BangDiem).where(BangDiem.ma_bang_diem.in_(journal["transcripts"]), BangDiem.cccd == user.cccd))
            db.execute(delete(ChungChi).where(ChungChi.ma_chung_chi.in_(journal["certificates"]), ChungChi.cccd == user.cccd))
            db.execute(delete(GiaiThuong).where(GiaiThuong.ma_giai_thuong.in_(journal["awards"]), GiaiThuong.cccd == user.cccd))
            db.delete(row)
            for field, value in journal["profile_before"].items():
                setattr(candidate, field, value)
            # Dữ liệu đã hoàn tác nhưng chưa giải phóng CCCD cho đến khi Storage xác nhận dọn xong.
            op.journal = {**op.journal, "data_rolled_back": True, "lease_until": 0}
            op.status = "cleanup_pending"
    else:
        raise TrangThaiKhongHopLe("Lệnh không được hỗ trợ")
    db.flush()
    return committed_output(db, op)

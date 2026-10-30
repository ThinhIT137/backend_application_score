from sqlalchemy import case, select, update, text
from sqlalchemy.orm import Session

from src.core.exceptions import ForbiddenError, HoSoNotFound, TrangThaiKhongHopLe, DuLieuKhongHopLe
from src.models.admission import ChuongTrinhDaoTao
from src.models.ho_so import NguyenVongSinhVien
from src.models.tham_chieu import ThiSinh
from src.models.trang_thai_ho_so import NguonDuLieu, TrangThaiHoSo
from src.models.workflow import NotificationOutbox
from src.schemas.candidate_preferences_schema import ReorderPreferences
from src.models.submission_operation import SubmissionOperation
from src.models.diem_thi_sinh import ChungChi
from src.models.giai_thuong import GiaiThuong
from datetime import datetime
from uuid import uuid4
import re


def pending_self_submission(row: NguyenVongSinhVien) -> bool:
    """A pending label alone is insufficient if processing metadata already exists."""
    return (row.trang_thai == TrangThaiHoSo.cho
            and row.nguon_du_lieu == NguonDuLieu.tu_nop
            and all(getattr(row, name, None) is None for name in (
                "ma_admin_xu_ly", "diem_uu_tien_ap_dung", "tong_diem_xet_tuyen",
                "ket_qua", "nguon_ket_qua", "diem_trace", "chot_ket_qua_at", "cong_bo_at")))


def changeable_self_submission(row: NguyenVongSinhVien) -> bool:
    return (row.trang_thai in (TrangThaiHoSo.cho, TrangThaiHoSo.hop_le)
            and row.nguon_du_lieu == NguonDuLieu.tu_nop
            and row.chot_ket_qua_at is None and row.cong_bo_at is None)


class CandidatePreferencesService:
    def __init__(self, db: Session):
        self.db = db

    def _lock_candidate(self, user):
        if user.role != "thi_sinh" or not user.cccd:
            raise ForbiddenError("Cần đăng nhập bằng tài khoản thí sinh")
        student = self.db.scalar(select(ThiSinh).where(ThiSinh.cccd == user.cccd)
                                 .with_for_update().execution_options(populate_existing=True))
        if student is None:
            raise HoSoNotFound("Không tìm thấy thông tin của bạn")

    def _require_editable(self, rows):
        from src.models.submission_operation import SubmissionOperation
        if rows and self.db.scalar(select(SubmissionOperation.operation_id).where(
                SubmissionOperation.dossier_id.in_([row.ma_ho_so for row in rows]),
                SubmissionOperation.status != "completed")):
            raise TrangThaiKhongHopLe("Hồ sơ đang lưu minh chứng, chưa thể thay đổi")
        if any(not pending_self_submission(row) for row in rows):
            raise TrangThaiKhongHopLe("Hồ sơ đã được xử lý hoặc không phải hồ sơ tự nộp")
        if rows and self.db.scalar(select(NotificationOutbox.ma_ho_so)
                .where(NotificationOutbox.ma_ho_so.in_([row.ma_ho_so for row in rows])).limit(1)):
            raise TrangThaiKhongHopLe("Hồ sơ đã có thông báo kết quả")

    def reorder(self, payload: ReorderPreferences, user):
        # Same first lock as submit/Storage replacement; prevents phantom submissions.
        self._lock_candidate(user)
        rows = list(self.db.scalars(select(NguyenVongSinhVien).where(
            NguyenVongSinhVien.cccd == user.cccd,
            NguyenVongSinhVien.nam_tuyen_sinh == payload.nam_tuyen_sinh)
            .order_by(NguyenVongSinhVien.ma_ho_so).with_for_update()
            .execution_options(populate_existing=True)).all())
        current = {row.ma_ho_so: row.nguyen_vong for row in rows}
        expected = {item.ma_ho_so: item.nguyen_vong_cu for item in payload.thu_tu}
        if any(key not in current for key in expected):
            raise HoSoNotFound("Không tìm thấy hồ sơ của bạn trong năm đã chọn")
        if current != expected:
            raise TrangThaiKhongHopLe("Danh sách nguyện vọng đã thay đổi. Hãy tải lại trước khi lưu")
        self._require_editable(rows)
        ranks = sorted(current.values())
        if len(ranks) != len(set(ranks)) or any(rank < 1 for rank in ranks):
            raise TrangThaiKhongHopLe("Thứ tự hiện tại cần được cán bộ tuyển sinh kiểm tra")
        order = {item.ma_ho_so: rank for item, rank in zip(payload.thu_tu, ranks)}
        # Preserve original rank numbers (including gaps) without temporary ranks.
        self.db.execute(update(NguyenVongSinhVien)
            .where(NguyenVongSinhVien.cccd == user.cccd,
                   NguyenVongSinhVien.nam_tuyen_sinh == payload.nam_tuyen_sinh,
                   NguyenVongSinhVien.ma_ho_so.in_(order))
            .values(nguyen_vong=case(order, value=NguyenVongSinhVien.ma_ho_so))
            .execution_options(synchronize_session=False))
        self.db.flush()
        for row in rows:
            self.db.expire(row)
        # get_db owns the whole transaction and releases all locks at commit/rollback.
        return {"success": True, "nam_tuyen_sinh": payload.nam_tuyen_sinh}

    def withdraw(self, ma_ho_so: str, user):
        self._lock_candidate(user)
        row = self.db.scalar(select(NguyenVongSinhVien).where(
            NguyenVongSinhVien.ma_ho_so == ma_ho_so,
            NguyenVongSinhVien.cccd == user.cccd).with_for_update()
            .execution_options(populate_existing=True))
        if row is None:
            previous = self.db.scalar(select(SubmissionOperation).where(
                SubmissionOperation.dossier_id == ma_ho_so,
                SubmissionOperation.cccd == user.cccd,
                SubmissionOperation.status == "withdraw_cleanup"))
            if previous:
                return self.cleanup_output(previous)
            raise HoSoNotFound("Không tìm thấy hồ sơ của bạn")
        self._require_editable([row])
        if self.db.scalar(select(SubmissionOperation.operation_id).where(
                SubmissionOperation.cccd == user.cccd,
                SubmissionOperation.status.in_(["pending", "aborting", "cleanup_pending", "withdraw_cleanup"]))):
            raise TrangThaiKhongHopLe("Cần hoàn tất lưu hoặc dọn minh chứng trước khi rút")
        source_operation = self.db.scalar(select(SubmissionOperation).where(
            SubmissionOperation.dossier_id == ma_ho_so, SubmissionOperation.cccd == user.cccd))
        if source_operation:
            source_operation.status = "withdrawn"
        self.db.delete(row)
        self.db.flush()
        # Evidence is candidate-scoped: any other dossier (including older years)
        # still references it. Only the last withdrawal may retire those objects.
        if not self.db.scalar(select(NguyenVongSinhVien.ma_ho_so).where(
                NguyenVongSinhVien.cccd == user.cccd).limit(1)):
            keys = set()
            for model in (ChungChi, GiaiThuong):
                for item in self.db.scalars(select(model).where(model.cccd == user.cccd)).all():
                    key = item.file_dinh_kem or ""
                    if re.fullmatch(re.escape(user.cccd) + r"/[\da-f-]{36}\.(pdf|jpg|png)", key):
                        keys.add(key)
                        self.db.delete(item)
            # Include uploaded objects from earlier withdrawn submissions, even
            # if their metadata has since changed. Never enumerate another user.
            operations = self.db.scalars(select(SubmissionOperation).where(
                SubmissionOperation.cccd == user.cccd)).all()
            for operation in operations:
                for file in operation.journal.get("files", []):
                    key = file.get("key", "")
                    if re.fullmatch(re.escape(user.cccd) + r"/[\da-f-]{36}\.(pdf|jpg|png)", key):
                        keys.add(key)
            if keys:
                op = next((o for o in operations if o.dossier_id == ma_ho_so), None)
                if op is None:
                    op = SubmissionOperation(operation_id=str(uuid4()), cccd=user.cccd,
                        dossier_id=ma_ho_so, payload_hash="", journal={}, created_at=datetime.now())
                    self.db.add(op)
                op.status = "withdraw_cleanup"
                op.journal = {**op.journal, "withdraw_files": sorted(keys)}
                self.db.flush()
                return self.cleanup_output(op)
        return {"success": True, "ma_ho_so": ma_ho_so}

    @staticmethod
    def cleanup_output(op):
        return {"success": True, "ma_ho_so": op.dossier_id,
                "operation_id": op.operation_id, "files": op.journal["withdraw_files"]}

    def pending_cleanup(self, user):
        self._lock_candidate(user)
        return [self.cleanup_output(op) for op in self.db.scalars(
            select(SubmissionOperation).where(SubmissionOperation.cccd == user.cccd,
                SubmissionOperation.status == "withdraw_cleanup")).all()]

    def complete_cleanup(self, operation_id, proof, user):
        from jose import jwt, JWTError
        from src.core.config import get_settings
        if not isinstance(proof, str):
            raise ForbiddenError("Xác nhận dọn minh chứng không hợp lệ")
        try:
            claims = jwt.decode(proof, get_settings().jwt_secret, algorithms=["HS256"],
                audience="withdraw-cleanup", options={"require_exp": True})
            if claims.get("sub") != user.cccd or claims.get("operation_id") != operation_id:
                raise ValueError()
        except (JWTError, ValueError):
            raise ForbiddenError("Xác nhận dọn minh chứng không hợp lệ")
        self._lock_candidate(user)
        op = self.db.get(SubmissionOperation, operation_id)
        if not op or op.cccd != user.cccd:
            raise HoSoNotFound("Không tìm thấy yêu cầu dọn minh chứng")
        if op.status not in ("withdraw_cleanup", "withdrawn"):
            raise TrangThaiKhongHopLe("Yêu cầu dọn không hợp lệ")
        op.status = "withdrawn"
        self.db.flush()
        return {"success": True}

    def change_program(self, ma_ho_so, payload, user):
        self._lock_candidate(user)
        row = self.db.scalar(select(NguyenVongSinhVien).where(
            NguyenVongSinhVien.ma_ho_so == ma_ho_so,
            NguyenVongSinhVien.cccd == user.cccd).with_for_update()
            .execution_options(populate_existing=True))
        if row is None:
            raise HoSoNotFound("Không tìm thấy hồ sơ của bạn")
        if not changeable_self_submission(row):
            raise TrangThaiKhongHopLe("Chỉ được đổi ngành khi hồ sơ chờ kiểm tra hoặc hợp lệ")
        from src.models.submission_operation import SubmissionOperation
        if self.db.scalar(select(SubmissionOperation.operation_id).where(
                SubmissionOperation.dossier_id == ma_ho_so,
                SubmissionOperation.status != "completed")) or self.db.get(NotificationOutbox, ma_ho_so):
            raise TrangThaiKhongHopLe("Hồ sơ đang lưu minh chứng hoặc đã có kết quả")
        if row.ma_chuong_trinh == payload.ma_chuong_trinh:
            return {"success": True, "ma_ho_so": ma_ho_so, "changed": False}
        if row.ma_chuong_trinh != payload.ma_chuong_trinh_cu:
            raise TrangThaiKhongHopLe("Ngành đã thay đổi. Vui lòng tải lại hồ sơ")
        if not self.db.get(ChuongTrinhDaoTao, payload.ma_chuong_trinh):
            raise DuLieuKhongHopLe("Chương trình không tồn tại")
        duplicate = self.db.scalar(select(NguyenVongSinhVien.ma_ho_so).where(
            NguyenVongSinhVien.cccd == user.cccd,
            NguyenVongSinhVien.nam_tuyen_sinh == row.nam_tuyen_sinh,
            NguyenVongSinhVien.ma_chuong_trinh == payload.ma_chuong_trinh,
            NguyenVongSinhVien.ma_ho_so != ma_ho_so))
        if duplicate:
            raise TrangThaiKhongHopLe("Bạn đã có hồ sơ cho chương trình này trong năm tuyển sinh")
        if row.ma_to_hop and not self.db.execute(text(
                "SELECT 1 FROM ctdt_to_hop WHERE ma_chuong_trinh=:program AND ma_to_hop=:combination AND nam=:year"),
                {"program": payload.ma_chuong_trinh, "combination": row.ma_to_hop,
                 "year": row.nam_tuyen_sinh}).first():
            raise DuLieuKhongHopLe("Chương trình mới không nhận tổ hợp hiện tại trong năm tuyển sinh")
        row.ma_chuong_trinh = payload.ma_chuong_trinh
        row.trang_thai = TrangThaiHoSo.cho
        for field in ("ma_admin_xu_ly", "diem_uu_tien_ap_dung", "tong_diem_xet_tuyen",
                      "ket_qua", "nguon_ket_qua", "diem_trace", "chot_ket_qua_at", "cong_bo_at"):
            setattr(row, field, None)
        self.db.flush()
        return {"success": True, "ma_ho_so": ma_ho_so, "changed": True}

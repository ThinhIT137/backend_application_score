from sqlalchemy import case, select, update
from sqlalchemy.orm import Session

from src.core.exceptions import ForbiddenError, HoSoNotFound, TrangThaiKhongHopLe
from src.models.ho_so import NguyenVongSinhVien
from src.models.tham_chieu import ThiSinh
from src.models.trang_thai_ho_so import NguonDuLieu, TrangThaiHoSo
from src.models.workflow import NotificationOutbox
from src.schemas.candidate_preferences_schema import ReorderPreferences


def pending_self_submission(row: NguyenVongSinhVien) -> bool:
    """A pending label alone is insufficient if processing metadata already exists."""
    return (row.trang_thai == TrangThaiHoSo.cho
            and row.nguon_du_lieu == NguonDuLieu.tu_nop
            and all(getattr(row, name, None) is None for name in (
                "ma_admin_xu_ly", "diem_uu_tien_ap_dung", "tong_diem_xet_tuyen",
                "ket_qua", "nguon_ket_qua", "diem_trace", "chot_ket_qua_at", "cong_bo_at")))


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
            raise HoSoNotFound("Không tìm thấy hồ sơ của bạn")
        self._require_editable([row])
        # Evidence belongs to the candidate and is shared across dossiers.
        self.db.delete(row)
        self.db.flush()
        return {"success": True, "ma_ho_so": ma_ho_so}

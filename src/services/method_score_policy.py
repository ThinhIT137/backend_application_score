import math
from sqlalchemy import select
from src.models.admission import PhuongThucXetTuyen
from src.core.exceptions import DuLieuKhongHopLe


def validate_method_score(db, code, score):
    # Same row lock as the admin configuration writer; ranges cannot change
    # between validation and the cutoff commit.
    method = db.scalar(select(PhuongThucXetTuyen).where(
        PhuongThucXetTuyen.ma_phuong_thuc == code).with_for_update()
        .execution_options(populate_existing=True))
    if not method or method.nhom_xet_tuyen not in (
            'THPT', 'HOC_BA', 'HSA', 'TSA', 'KET_HOP', 'TUYEN_THANG', 'KHAC'):
        raise DuLieuKhongHopLe("Phương thức chưa được cấu hình nhóm xét tuyển")
    low, high = method.diem_toi_thieu, method.diem_toi_da
    if low is None or high is None or not math.isfinite(low) or not math.isfinite(high) or not 0 <= low < high:
        raise DuLieuKhongHopLe("Phương thức chưa có thang điểm hợp lệ")
    if not math.isfinite(score) or not low <= score <= high:
        raise DuLieuKhongHopLe(f"Điểm phương thức phải trong khoảng {low}–{high}")

from __future__ import annotations

# ---------------------------------------------------------------------------
# Dai diem hop le cho tung loai chung chi/bai thi
# Moi entry: (min, max, buoc)  -- buoc=None nghia la chi can nam trong [min, max]
# QUAN TRONG: Day la khung uoc tinh pho bien chua co bang chuan chinh thuc.
# Khi nhom co so lieu that, chi sua dict DIEM_HOP_LE nay -- 1 noi duy nhat.
# V-ACT/TSA can xac nhan lai voi nhom truoc go-live.
# ---------------------------------------------------------------------------
DIEM_HOP_LE: dict[str, tuple[float, float, float | None]] = {
    "IELTS":     (0.0,    9.0,   0.5),
    "TOEFL_IBT": (0.0,  120.0,   1.0),
    "TOEIC":     (0.0,  990.0,   1.0),
    "SAT":       (400.0, 1600.0, 1.0),
    "ACT":       (1.0,   36.0,   1.0),
    "THPT":      (0.0,   10.0,   0.25),
    "HSA":       (0.0,  150.0,   1.0),
    # TODO: xac nhan lai V-ACT/TSA voi nhom
    "VACT":      (0.0,  100.0,   None),
    "TSA":       (0.0,  100.0,   None),
}

DIEM_UU_TIEN_TOI_DA: float = 2.75
THANG_DIEM_CHUAN: float = 30.0
LOAI_CHUNG_CHI_DGNL: str = "DGNL"

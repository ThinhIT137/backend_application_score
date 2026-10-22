DECISIONS = {"do": "trung_tuyen", "truot": "khong_trung_tuyen"}


def published(record) -> bool:
    return bool(getattr(record, "cong_bo_at", None)) and getattr(record, "trang_thai", None) in DECISIONS


def result_label(record) -> str:
    return DECISIONS[record.trang_thai] if published(record) else "chua_cong_bo"


def public_status(record):
    from src.models.trang_thai_ho_so import TrangThaiHoSo
    status = record.trang_thai
    return TrangThaiHoSo.dang_xu_ly if status in DECISIONS and not published(record) else status

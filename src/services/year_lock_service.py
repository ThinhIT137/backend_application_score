from datetime import datetime
from sqlalchemy import text
from src.models.year_lock import AdmissionYearLock
from src.core.exceptions import DuLieuKhongHopLe, TrangThaiKhongHopLe


def year_lock(db, year):
    if db.bind.dialect.name == 'postgresql':
        # A row may not exist yet. Advisory locking also serializes first lock
        # creation with all cutoff writers for that year.
        db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': 71030000 + year})
    return db.get(AdmissionYearLock, year, populate_existing=True)


def require_open_year(db, year):
    if year_lock(db, year):
        raise TrangThaiKhongHopLe("Điểm năm tuyển sinh này đã khóa")


def lock_year(db, year, confirmation, admin):
    if not 2000 <= year <= 2100 or confirmation != year:
        raise DuLieuKhongHopLe("Nhập đúng năm cần khóa để xác nhận")
    current = year_lock(db, year)
    if not current:
        current = AdmissionYearLock(nam=year, ma_admin=admin.ma_admin, locked_at=datetime.now())
        db.add(current)
        db.flush()
    return {'nam': year, 'locked': True, 'locked_at': current.locked_at}

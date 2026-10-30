from datetime import datetime
from sqlalchemy import Integer, DateTime, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from src.core.database import Base


class AdmissionYearLock(Base):
    __tablename__ = 'admission_year_lock'
    nam: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    locked_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    ma_admin: Mapped[str] = mapped_column(String, ForeignKey('admin.ma_admin'), nullable=False)

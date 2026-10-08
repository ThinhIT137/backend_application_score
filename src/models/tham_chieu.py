"""Bảng tham chiếu đã có sẵn -- chỉ map cột tối thiểu cần cho Sprint 1 & 2."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ThiSinh(Base):
    __tablename__ = "thi_sinh"

    cccd: Mapped[str] = mapped_column(String(12), primary_key=True)


class Admin(Base):
    __tablename__ = "admin"

    ma_admin: Mapped[str] = mapped_column(String, primary_key=True)


class DanhMucMonHoc(Base):
    __tablename__ = "danh_muc_mon_hoc"

    ma_mon: Mapped[str] = mapped_column(String, primary_key=True)


class LoTrinhTuyenSinh(Base):
    __tablename__ = "lo_trinh_tuyen_sinh"

    ma_lo_trinh: Mapped[str] = mapped_column(String, primary_key=True)
    nam_tuyen_sinh: Mapped[int] = mapped_column(Integer, nullable=False)
    loai_moc: Mapped[str | None] = mapped_column(String, nullable=True)
    ten_moc: Mapped[str | None] = mapped_column(String, nullable=True)
    thoi_gian_bat_dau: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    thoi_gian_ket_thuc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

"""Bảng tham chiếu đã có sẵn — chỉ map cột tối thiểu cần cho Sprint 2.

Cột thời gian của `lo_trinh_tuyen_sinh` giả định theo snake_case phổ biến
(`thoi_gian_bat_dau` / `thoi_gian_ket_thuc` / `loai_moc`). Nếu Prisma map khác,
chỉnh lại mapped_column cho khớp schema.prisma, không tạo bảng mới.
"""

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


class GiaiThuong(Base):
    __tablename__ = "giai_thuong"

    ma_giai_thuong: Mapped[str] = mapped_column(String, primary_key=True)
    cccd: Mapped[str] = mapped_column(String(12), nullable=False)


class LoTrinhTuyenSinh(Base):
    __tablename__ = "lo_trinh_tuyen_sinh"

    ma_lo_trinh: Mapped[str] = mapped_column(String, primary_key=True)
    nam_tuyen_sinh: Mapped[int] = mapped_column(Integer, nullable=False)
    loai_moc: Mapped[str | None] = mapped_column(String, nullable=True)
    ten_moc: Mapped[str | None] = mapped_column(String, nullable=True)
    thoi_gian_bat_dau: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    thoi_gian_ket_thuc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

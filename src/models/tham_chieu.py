"""Reference mappings match the existing Prisma tables and enum names."""

from datetime import datetime

from sqlalchemy import DateTime, String, ForeignKey, Integer
from sqlalchemy.orm import synonym
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ThiSinh(Base):
    __tablename__ = "thi_sinh"

    cccd: Mapped[str] = mapped_column(String(12), primary_key=True)
    ho_ten: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    password: Mapped[str | None] = mapped_column(String, nullable=True)
    activation_otp_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    activation_otp_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    activation_otp_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    activation_otp_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    so_dien_thoai: Mapped[str | None] = mapped_column(String, nullable=True)
    khu_vuc: Mapped[str | None] = mapped_column(String, nullable=True)
    doi_tuong_uu_tien: Mapped[str | None] = mapped_column(String, nullable=True)


class Admin(Base):
    __tablename__ = "admin"

    ma_admin: Mapped[str] = mapped_column(String, primary_key=True)


class DanhMucMonHoc(Base):
    __tablename__ = "danh_muc_mon_hoc"

    ma_mon: Mapped[str] = mapped_column(String, primary_key=True)


class LoTrinhTuyenSinh(Base):
    __tablename__ = "lo_trinh_tuyen_sinh"

    ma_su_kien: Mapped[str] = mapped_column(String, primary_key=True)
    ten_su_kien: Mapped[str] = mapped_column(String, nullable=False)
    ghi_chu: Mapped[str | None] = mapped_column(String, nullable=True)
    ma_admin_cap_nhat: Mapped[str] = mapped_column(ForeignKey("admin.ma_admin"))
    ten_moc = synonym("ten_su_kien")

    @property
    def loai_moc(self):
        return ""
    thoi_gian_bat_dau: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    thoi_gian_ket_thuc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

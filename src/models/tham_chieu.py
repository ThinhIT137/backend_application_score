"""Reference mappings match the existing Prisma tables and enum names."""

from datetime import datetime

import enum
from sqlalchemy import DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import synonym
from src.models.trang_thai_ho_so import pg_enum
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


class HangGiaiThuong(str, enum.Enum):
    giai_nhat = "giai_nhat"
    giai_nhi = "giai_nhi"
    giai_ba = "giai_ba"
    khuyen_khich = "khuyen_khich"

class CapGiaiThuong(str, enum.Enum):
    toan_quoc = "toan_quoc"
    tinh = "tinh"
    mien_bac = "mien_bac"
    mien_nam = "mien_nam"

class MonHoc(str, enum.Enum):
    toan = "toan"
    van = "van"
    anh = "anh"
    vat_ly = "vat_ly"
    hoa_hoc = "hoa_hoc"
    sinh_hoc = "sinh_hoc"
    dia_ly = "dia_ly"
    lich_su = "lich_su"
    gdcd = "gdcd"
    tin_hoc = "tin_hoc"

class GiaiThuong(Base):
    __tablename__ = "giai_thuong"

    ma_giai_thuong: Mapped[str] = mapped_column(String, primary_key=True)
    cccd: Mapped[str] = mapped_column(String(12), ForeignKey("thi_sinh.cccd"), nullable=False)
    giai_thuong: Mapped[HangGiaiThuong] = mapped_column(pg_enum(HangGiaiThuong, "hang_giai_thuong"))
    loai_giai_thuong: Mapped[CapGiaiThuong] = mapped_column(pg_enum(CapGiaiThuong, "cap_giai_thuong"))
    mon_hoc: Mapped[MonHoc] = mapped_column(pg_enum(MonHoc, "mon_hoc_enum"))


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

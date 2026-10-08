import enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.models.trang_thai_ho_so import pg_enum


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
    """Giai thuong hoc sinh gioi -- minh chung nop ho so giai thuong."""

    __tablename__ = "giai_thuong"

    ma_giai_thuong: Mapped[str] = mapped_column(String, primary_key=True)
    cccd: Mapped[str] = mapped_column(
        String(12), ForeignKey("thi_sinh.cccd", ondelete="CASCADE"), nullable=False
    )
    giai_thuong: Mapped[HangGiaiThuong] = mapped_column(
        pg_enum(HangGiaiThuong, "hang_giai_thuong"), nullable=False
    )
    loai_giai_thuong: Mapped[CapGiaiThuong] = mapped_column(
        pg_enum(CapGiaiThuong, "cap_giai_thuong"), nullable=False
    )
    mon_hoc: Mapped[MonHoc] = mapped_column(
        pg_enum(MonHoc, "mon_hoc_enum"), nullable=False
    )
    # Ghi chu: KHONG co cot file_dinh_kem o Sprint 1.
    # Bo sung sau neu nhom xac nhan can minh chung giai thuong.

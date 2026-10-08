from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base
from src.models.trang_thai_ho_so import LoaiBangDiem, TrangThaiDuyet, pg_enum


class BangDiem(Base):
    __tablename__ = "bang_diem"

    ma_bang_diem: Mapped[str] = mapped_column(String, primary_key=True)
    cccd: Mapped[str] = mapped_column(String(12), ForeignKey("thi_sinh.cccd"), nullable=False)
    loai_diem: Mapped[LoaiBangDiem] = mapped_column(
        pg_enum(LoaiBangDiem, "loai_bang_diem"),
        nullable=False,
    )
    nam_hoc: Mapped[int] = mapped_column(Integer, nullable=False)

    chi_tiet: Mapped[list["DiemChiTiet"]] = relationship(back_populates="bang_diem")


class DiemChiTiet(Base):
    __tablename__ = "diem_chi_tiet"

    ma_chi_tiet: Mapped[str] = mapped_column(String, primary_key=True)
    ma_bang_diem: Mapped[str] = mapped_column(
        String, ForeignKey("bang_diem.ma_bang_diem"), nullable=False
    )
    ma_mon: Mapped[str] = mapped_column(
        String, ForeignKey("danh_muc_mon_hoc.ma_mon"), nullable=False
    )
    diem_so: Mapped[float | None] = mapped_column(Float, nullable=True)

    bang_diem: Mapped[BangDiem] = relationship(back_populates="chi_tiet")


class ChungChi(Base):
    __tablename__ = "chung_chi"

    ma_chung_chi: Mapped[str] = mapped_column(String, primary_key=True)
    cccd: Mapped[str] = mapped_column(String(12), ForeignKey("thi_sinh.cccd"), nullable=False)
    loai_chung_chi: Mapped[str] = mapped_column(String, nullable=False)
    diem_hoac_hang: Mapped[str | None] = mapped_column(String, nullable=True)
    ngay_cap: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ngay_het_han: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    file_dinh_kem: Mapped[str | None] = mapped_column(String, nullable=True)
    trang_thai_duyet: Mapped[TrangThaiDuyet] = mapped_column(
        pg_enum(TrangThaiDuyet, "trang_thai_duyet"),
        nullable=False,
        default=TrangThaiDuyet.cho,
    )
    create_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

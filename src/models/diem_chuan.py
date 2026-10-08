from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base

if TYPE_CHECKING:
    pass


class LichSuDiemChuan(Base):
    """Diem chuan cua 1 chuong trinh dao tao trong 1 nam tuyen sinh."""

    __tablename__ = "lich_su_diem_chuan"
    __table_args__ = (
        UniqueConstraint("ma_chuong_trinh", "nam", name="uq_ls_dc_chuong_trinh_nam"),
    )

    ma_ls_dc: Mapped[str] = mapped_column(String, primary_key=True)
    ma_chuong_trinh: Mapped[str] = mapped_column(
        String, ForeignKey("chuong_trinh_dao_tao.ma_chuong_trinh"), nullable=False
    )
    nam: Mapped[int] = mapped_column(Integer, nullable=False)
    chi_tieu: Mapped[int] = mapped_column(Integer, nullable=False)
    # So luong trung tuyen thuc te -- chi co gia tri sau khi ket thuc dot xet tuyen
    trung_tuyen: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ma_admin_cap_nhat: Mapped[str] = mapped_column(
        String, ForeignKey("admin.ma_admin"), nullable=False
    )
    create_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    diem_trung_tuyen: Mapped[list["DiemTrungTuyen"]] = relationship(
        back_populates="lich_su", cascade="all, delete-orphan"
    )


class DiemTrungTuyen(Base):
    """Diem trung tuyen theo tung phuong thuc xet tuyen trong 1 nam."""

    __tablename__ = "diem_trung_tuyen"
    __table_args__ = (
        UniqueConstraint("ma_ls_dc", "ma_phuong_thuc", name="uq_dtt_ls_dc_phuong_thuc"),
    )

    ma_diem_tt: Mapped[str] = mapped_column(String, primary_key=True)
    ma_ls_dc: Mapped[str] = mapped_column(
        String, ForeignKey("lich_su_diem_chuan.ma_ls_dc", ondelete="CASCADE"), nullable=False
    )
    ma_phuong_thuc: Mapped[str] = mapped_column(
        String, ForeignKey("phuong_thuc_xet_tuyen.ma_phuong_thuc"), nullable=False
    )
    diem: Mapped[float] = mapped_column(Float, nullable=False)
    create_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Tieu chi phu (tuy chon)
    nguyen_vong_toi_da: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dieu_kien_mon: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    diem_uu_tien_toi_thieu: Mapped[float | None] = mapped_column(Float, nullable=True)

    lich_su: Mapped[LichSuDiemChuan] = relationship(back_populates="diem_trung_tuyen")

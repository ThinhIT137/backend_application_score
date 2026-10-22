"""Mappings use existing Prisma tables; this service does not create production tables."""
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from src.core.database import Base


class NganhHoc(Base):
    __tablename__ = "nganh_hoc"

    ma_nganh: Mapped[str] = mapped_column(String, primary_key=True)
    ten_nganh: Mapped[str] = mapped_column(String, nullable=False)


class ChuongTrinhDaoTao(Base):
    __tablename__ = "chuong_trinh_dao_tao"

    ma_chuong_trinh: Mapped[str] = mapped_column(String, primary_key=True)
    ma_nganh: Mapped[str | None] = mapped_column(
        String, ForeignKey("nganh_hoc.ma_nganh"), nullable=True
    )
    ten_chuong_trinh: Mapped[str | None] = mapped_column(String, nullable=True)

class PhuongThucXetTuyen(Base):
    __tablename__ = "phuong_thuc_xet_tuyen"

    ma_phuong_thuc: Mapped[str] = mapped_column(String, primary_key=True)
    ten_phuong_thuc: Mapped[str | None] = mapped_column(String, nullable=True)

class ToHopXetTuyen(Base):
    __tablename__ = "to_hop_xet_tuyen"

    ma_to_hop: Mapped[str] = mapped_column(String, primary_key=True)
    ma_mon_1: Mapped[str | None] = mapped_column(String, nullable=True)
    ma_mon_2: Mapped[str | None] = mapped_column(String, nullable=True)
    ma_mon_3: Mapped[str | None] = mapped_column(String, nullable=True)


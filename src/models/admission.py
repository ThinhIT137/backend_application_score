"""Mappings use existing Prisma tables; this service does not create production tables."""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from src.core.database import Base

class ChuongTrinhDaoTao(Base):
    __tablename__ = "chuong_trinh_dao_tao"
    ma_chuong_trinh: Mapped[str] = mapped_column(String, primary_key=True)

class PhuongThucXetTuyen(Base):
    __tablename__ = "phuong_thuc_xet_tuyen"
    ma_phuong_thuc: Mapped[str] = mapped_column(String, primary_key=True)

class ToHopXetTuyen(Base):
    __tablename__ = "to_hop_xet_tuyen"
    ma_to_hop: Mapped[str] = mapped_column(String, primary_key=True)


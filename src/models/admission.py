"""Mappings use existing Prisma tables; this service does not create production tables."""
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
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

class LichSuDiemChuan(Base):
    __tablename__ = "lich_su_diem_chuan"
    __table_args__ = (UniqueConstraint("ma_chuong_trinh", "nam"),)
    ma_ls_dc: Mapped[str] = mapped_column(String, primary_key=True)
    ma_chuong_trinh: Mapped[str] = mapped_column(ForeignKey("chuong_trinh_dao_tao.ma_chuong_trinh"))
    nam: Mapped[int] = mapped_column(Integer)
    chi_tieu: Mapped[int] = mapped_column(Integer)
    trung_tuyen: Mapped[int | None] = mapped_column(Integer)
    ma_admin_cap_nhat: Mapped[str] = mapped_column(ForeignKey("admin.ma_admin"))
    create_at: Mapped[datetime] = mapped_column(DateTime)
    diem_trung_tuyen: Mapped[list["DiemTrungTuyen"]] = relationship(cascade="all, delete-orphan")

class DiemTrungTuyen(Base):
    __tablename__ = "diem_trung_tuyen"
    __table_args__ = (UniqueConstraint("ma_ls_dc", "ma_phuong_thuc"),)
    ma_diem_tt: Mapped[str] = mapped_column(String, primary_key=True)
    ma_ls_dc: Mapped[str] = mapped_column(ForeignKey("lich_su_diem_chuan.ma_ls_dc"))
    ma_phuong_thuc: Mapped[str] = mapped_column(ForeignKey("phuong_thuc_xet_tuyen.ma_phuong_thuc"))
    diem: Mapped[float] = mapped_column(Float)
    create_at: Mapped[datetime] = mapped_column(DateTime)

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.models.trang_thai_ho_so import NguonDuLieu, TrangThaiHoSo as TrangThaiDuyet, pg_enum


class NguyenVongSinhVien(Base):
    __tablename__ = "nguyen_vong_sinh_vien"

    ma_ho_so: Mapped[str] = mapped_column(String, primary_key=True)
    cccd: Mapped[str] = mapped_column(String(12), ForeignKey("thi_sinh.cccd"), nullable=False)
    ma_chuong_trinh: Mapped[str] = mapped_column(String, nullable=False)
    trang_thai: Mapped[TrangThaiDuyet] = mapped_column(
        pg_enum(TrangThaiDuyet, "trang_thai_ho_so"),
        nullable=False,
        default=TrangThaiDuyet.cho,
    )
    ket_qua: Mapped[str | None] = mapped_column(String, nullable=True)
    nguon_ket_qua: Mapped[str | None] = mapped_column(String, nullable=True)
    chot_ket_qua_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cong_bo_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    diem_trace: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    diem_uu_tien_ap_dung: Mapped[float | None] = mapped_column(Float, nullable=True)
    tong_diem_xet_tuyen: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma_to_hop: Mapped[str | None] = mapped_column(String, nullable=True)
    ma_phuong_thuc: Mapped[str] = mapped_column(String, nullable=False)
    nguon_du_lieu: Mapped[NguonDuLieu] = mapped_column(
        pg_enum(NguonDuLieu, "nguon_du_lieu"),
        nullable=False,
    )
    nguyen_vong: Mapped[int] = mapped_column(Integer, nullable=False)
    nam_tuyen_sinh: Mapped[int] = mapped_column(Integer, nullable=False)
    ma_admin_xu_ly: Mapped[str | None] = mapped_column(
        String, ForeignKey("admin.ma_admin"), nullable=True
    )
    create_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

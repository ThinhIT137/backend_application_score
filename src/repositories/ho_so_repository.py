from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from src.models.diem_chuan import BangDiem, ChungChi
from src.models.ho_so import NguyenVongSinhVien
from src.models.tham_chieu import GiaiThuong
from src.models.trang_thai_ho_so import TrangThaiDuyet
from src.repositories.ho_so_repository_interface import HoSoRepositoryInterface


class HoSoRepository(HoSoRepositoryInterface):
    def __init__(self, db: Session) -> None:
        self.db = db

    def _filter(
        self,
        stmt: Select[tuple[NguyenVongSinhVien]],
        *,
        trang_thai: TrangThaiDuyet | None = None,
        nam_tuyen_sinh: int | None = None,
        ma_chuong_trinh: str | None = None,
        ma_phuong_thuc: str | None = None,
    ) -> Select[tuple[NguyenVongSinhVien]]:
        if trang_thai is not None:
            stmt = stmt.where(NguyenVongSinhVien.trang_thai == trang_thai)
        if nam_tuyen_sinh is not None:
            stmt = stmt.where(NguyenVongSinhVien.nam_tuyen_sinh == nam_tuyen_sinh)
        if ma_chuong_trinh:
            stmt = stmt.where(NguyenVongSinhVien.ma_chuong_trinh == ma_chuong_trinh)
        if ma_phuong_thuc:
            stmt = stmt.where(NguyenVongSinhVien.ma_phuong_thuc == ma_phuong_thuc)
        return stmt

    def list_ho_so(
        self,
        *,
        trang_thai: TrangThaiDuyet | None,
        nam_tuyen_sinh: int | None,
        ma_chuong_trinh: str | None,
    ) -> list[NguyenVongSinhVien]:
        stmt = self._filter(
            select(NguyenVongSinhVien),
            trang_thai=trang_thai,
            nam_tuyen_sinh=nam_tuyen_sinh,
            ma_chuong_trinh=ma_chuong_trinh,
        ).order_by(NguyenVongSinhVien.create_at.desc())
        return list(self.db.scalars(stmt).all())

    def get_by_ma_ho_so(self, ma_ho_so: str) -> NguyenVongSinhVien | None:
        return self.db.get(NguyenVongSinhVien, ma_ho_so)

    def list_chung_chi_by_cccd(self, cccd: str) -> list[ChungChi]:
        stmt = select(ChungChi).where(ChungChi.cccd == cccd)
        return list(self.db.scalars(stmt).all())

    def list_giai_thuong_by_cccd(self, cccd: str) -> list[GiaiThuong]:
        stmt = select(GiaiThuong).where(GiaiThuong.cccd == cccd)
        return list(self.db.scalars(stmt).all())

    def list_bang_diem_by_cccd(self, cccd: str) -> list[BangDiem]:
        stmt = select(BangDiem).where(BangDiem.cccd == cccd)
        return list(self.db.scalars(stmt).all())

    def count_cho(
        self,
        *,
        nam_tuyen_sinh: int,
        ma_chuong_trinh: str | None,
        ma_phuong_thuc: str | None,
    ) -> int:
        stmt = select(func.count()).select_from(NguyenVongSinhVien).where(
            NguyenVongSinhVien.trang_thai == TrangThaiDuyet.cho,
            NguyenVongSinhVien.nam_tuyen_sinh == nam_tuyen_sinh,
        )
        if ma_chuong_trinh:
            stmt = stmt.where(NguyenVongSinhVien.ma_chuong_trinh == ma_chuong_trinh)
        if ma_phuong_thuc:
            stmt = stmt.where(NguyenVongSinhVien.ma_phuong_thuc == ma_phuong_thuc)
        return int(self.db.scalar(stmt) or 0)

    def list_for_cong_bo(
        self,
        *,
        nam_tuyen_sinh: int,
        ma_chuong_trinh: str | None,
        ma_phuong_thuc: str | None,
    ) -> list[NguyenVongSinhVien]:
        stmt = self._filter(
            select(NguyenVongSinhVien),
            nam_tuyen_sinh=nam_tuyen_sinh,
            ma_chuong_trinh=ma_chuong_trinh,
            ma_phuong_thuc=ma_phuong_thuc,
        )
        return list(self.db.scalars(stmt).all())

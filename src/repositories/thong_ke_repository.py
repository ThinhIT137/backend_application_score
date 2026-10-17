from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.admission import (
    ChuongTrinhDaoTao,
    NganhHoc,
    PhuongThucXetTuyen,
    ToHopXetTuyen,
)
from src.models.diem_chuan import DiemTrungTuyen, LichSuDiemChuan
from src.models.ho_so import NguyenVongSinhVien
from src.models.tham_chieu import ThiSinh


class ThongKeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_ho_so(
        self,
        *,
        nam_tuyen_sinh: int,
        tu_ngay: date | None = None,
        den_ngay: date | None = None,
        ma_chuong_trinh: str | None = None,
        ma_phuong_thuc: str | None = None,
        ma_to_hop: str | None = None,
    ) -> list[NguyenVongSinhVien]:
        stmt = select(NguyenVongSinhVien).where(
            NguyenVongSinhVien.nam_tuyen_sinh == nam_tuyen_sinh
        )
        if tu_ngay is not None:
            stmt = stmt.where(
                NguyenVongSinhVien.create_at >= datetime.combine(tu_ngay, time.min)
            )
        if den_ngay is not None:
            stmt = stmt.where(
                NguyenVongSinhVien.create_at <= datetime.combine(den_ngay, time.max)
            )
        if ma_chuong_trinh:
            stmt = stmt.where(
                NguyenVongSinhVien.ma_chuong_trinh == ma_chuong_trinh
            )
        if ma_phuong_thuc:
            stmt = stmt.where(NguyenVongSinhVien.ma_phuong_thuc == ma_phuong_thuc)
        if ma_to_hop:
            stmt = stmt.where(NguyenVongSinhVien.ma_to_hop == ma_to_hop)
        stmt = stmt.order_by(
            NguyenVongSinhVien.tong_diem_xet_tuyen.desc().nullslast(),
            NguyenVongSinhVien.create_at.desc(),
        )
        return list(self.db.scalars(stmt).all())

    def list_chuong_trinh(self) -> list[tuple[ChuongTrinhDaoTao, str | None]]:
        stmt = (
            select(ChuongTrinhDaoTao, NganhHoc.ten_nganh)
            .outerjoin(NganhHoc, ChuongTrinhDaoTao.ma_nganh == NganhHoc.ma_nganh)
            .order_by(ChuongTrinhDaoTao.ma_chuong_trinh)
        )
        return [(row[0], row[1]) for row in self.db.execute(stmt).all()]

    def list_chi_tieu(self, nam_tuyen_sinh: int) -> list[LichSuDiemChuan]:
        stmt = select(LichSuDiemChuan).where(
            LichSuDiemChuan.nam == nam_tuyen_sinh
        )
        return list(self.db.scalars(stmt).all())

    def list_phuong_thuc(self) -> list[PhuongThucXetTuyen]:
        return list(
            self.db.scalars(
                select(PhuongThucXetTuyen).order_by(
                    PhuongThucXetTuyen.ma_phuong_thuc
                )
            ).all()
        )

    def list_to_hop(self) -> list[ToHopXetTuyen]:
        return list(
            self.db.scalars(
                select(ToHopXetTuyen).order_by(ToHopXetTuyen.ma_to_hop)
            ).all()
        )

    def list_thi_sinh(self, cccds: set[str]) -> list[ThiSinh]:
        if not cccds:
            return []
        return list(
            self.db.scalars(select(ThiSinh).where(ThiSinh.cccd.in_(cccds))).all()
        )

    def list_diem_chuan(
        self, nam_tuyen_sinh: int
    ) -> list[tuple[str, str, float]]:
        stmt = (
            select(
                LichSuDiemChuan.ma_chuong_trinh,
                DiemTrungTuyen.ma_phuong_thuc,
                DiemTrungTuyen.diem,
            )
            .join(
                DiemTrungTuyen,
                DiemTrungTuyen.ma_ls_dc == LichSuDiemChuan.ma_ls_dc,
            )
            .where(LichSuDiemChuan.nam == nam_tuyen_sinh)
        )
        return [(row[0], row[1], float(row[2])) for row in self.db.execute(stmt)]

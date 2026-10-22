from uuid import uuid4

from sqlalchemy import extract, select
from sqlalchemy.orm import Session

from src.models.diem_thi_sinh import BangDiem, ChungChi, DiemChiTiet
from src.models.tham_chieu import DanhMucMonHoc, LoTrinhTuyenSinh, ThiSinh
from src.models.trang_thai_ho_so import LoaiBangDiem, TrangThaiDuyet
from src.repositories.diem_repository_interface import DiemRepositoryInterface
from src.schemas.diem_schema import DiemMonThpt, LOAI_CHUNG_CHI_DGNL


class DiemRepository(DiemRepositoryInterface):
    def __init__(self, db: Session) -> None:
        self.db = db

    def thi_sinh_exists(self, cccd: str) -> bool:
        return self.db.get(ThiSinh, cccd) is not None

    def mon_exists(self, ma_mon: str) -> bool:
        return self.db.get(DanhMucMonHoc, ma_mon) is not None

    def get_bang_diem_tnthpt(self, cccd: str, nam_hoc: int) -> BangDiem | None:
        stmt = select(BangDiem).where(
            BangDiem.cccd == cccd,
            BangDiem.nam_hoc == nam_hoc,
            BangDiem.loai_diem == LoaiBangDiem.tnTHPT,
        )
        return self.db.scalars(stmt).first()

    def upsert_bang_diem_tnthpt(
        self, cccd: str, nam_hoc: int, diem_mon: list[DiemMonThpt]
    ) -> BangDiem:
        with self.db.begin_nested():
            bang = self.get_bang_diem_tnthpt(cccd, nam_hoc)
            if bang is None:
                bang = BangDiem(
                    ma_bang_diem=str(uuid4()),
                    cccd=cccd,
                    loai_diem=LoaiBangDiem.tnTHPT,
                    nam_hoc=nam_hoc,
                )
                self.db.add(bang)
                self.db.flush()
            else:
                existing = list(
                    self.db.scalars(
                        select(DiemChiTiet).where(DiemChiTiet.ma_bang_diem == bang.ma_bang_diem)
                    ).all()
                )
                for row in existing:
                    self.db.delete(row)
                self.db.flush()

            for mon in diem_mon:
                self.db.add(
                    DiemChiTiet(
                        ma_chi_tiet=str(uuid4()),
                        ma_bang_diem=bang.ma_bang_diem,
                        ma_mon=mon.ma_mon,
                        diem_so=mon.diem_so,
                    )
                )
            self.db.flush()
            return bang

    def list_lo_trinh(self, nam_tuyen_sinh: int) -> list[LoTrinhTuyenSinh]:
        stmt = select(LoTrinhTuyenSinh).where(extract("year", LoTrinhTuyenSinh.thoi_gian_bat_dau) == nam_tuyen_sinh)
        return list(self.db.scalars(stmt).all())

    def find_dgnl_trung(self, cccd: str, nam: int) -> ChungChi | None:
        stmt = select(ChungChi).where(
            ChungChi.cccd == cccd,
            ChungChi.loai_chung_chi == LOAI_CHUNG_CHI_DGNL,
            extract("year", ChungChi.ngay_cap) == nam,
        )
        return self.db.scalars(stmt).first()

    def create_chung_chi(self, chung_chi: ChungChi) -> ChungChi:
        self.db.add(chung_chi)
        self.db.flush()
        return chung_chi

    def list_dgnl_cho(self) -> list[ChungChi]:
        stmt = select(ChungChi).where(
            ChungChi.loai_chung_chi == LOAI_CHUNG_CHI_DGNL,
            ChungChi.trang_thai_duyet == TrangThaiDuyet.cho,
        )
        return list(self.db.scalars(stmt).all())

    def get_chung_chi(self, ma_chung_chi: str) -> ChungChi | None:
        return self.db.get(ChungChi, ma_chung_chi)

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.diem_chuan import DiemTrungTuyen, LichSuDiemChuan
from src.repositories.diem_chuan_repository_interface import DiemChuanRepositoryInterface


class DiemChuanRepository(DiemChuanRepositoryInterface):
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(
        self, ma_chuong_trinh: str | None = None, nam: int | None = None
    ) -> list[LichSuDiemChuan]:
        stmt = select(LichSuDiemChuan)
        if ma_chuong_trinh:
            stmt = stmt.where(LichSuDiemChuan.ma_chuong_trinh == ma_chuong_trinh)
        if nam:
            stmt = stmt.where(LichSuDiemChuan.nam == nam)
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, ma_ls_dc: str) -> LichSuDiemChuan | None:
        return self.db.get(LichSuDiemChuan, ma_ls_dc)

    def get_by_chuong_trinh_nam(self, ma_chuong_trinh: str, nam: int) -> LichSuDiemChuan | None:
        stmt = select(LichSuDiemChuan).where(
            LichSuDiemChuan.ma_chuong_trinh == ma_chuong_trinh,
            LichSuDiemChuan.nam == nam,
        )
        return self.db.scalars(stmt).first()

    def create(self, record: LichSuDiemChuan) -> LichSuDiemChuan:
        from src.services.year_lock_service import require_open_year
        require_open_year(self.db, record.nam)
        self.db.add(record)
        self.db.flush()
        self.db.refresh(record)
        return record

    def update(self, record: LichSuDiemChuan) -> LichSuDiemChuan:
        self.db.flush()
        self.db.refresh(record)
        return record

    def delete(self, ma_ls_dc: str) -> None:
        record = self.get_by_id(ma_ls_dc)
        if record:
            from src.services.year_lock_service import require_open_year
            require_open_year(self.db, record.nam)
            self.db.delete(record)
            self.db.flush()

    def add_diem_trung_tuyen(self, dtt: DiemTrungTuyen) -> DiemTrungTuyen:
        from src.services.method_score_policy import validate_method_score
        from src.services.year_lock_service import require_open_year
        require_open_year(self.db, self.db.get(LichSuDiemChuan, dtt.ma_ls_dc).nam)
        validate_method_score(self.db, dtt.ma_phuong_thuc, dtt.diem)
        self.db.add(dtt)
        self.db.flush()
        self.db.refresh(dtt)
        return dtt

    def list_diem_trung_tuyen_by_ls(
        self, ma_ls_dc: str, nam: int | None = None
    ) -> list[DiemTrungTuyen]:
        stmt = select(DiemTrungTuyen).where(DiemTrungTuyen.ma_ls_dc == ma_ls_dc)
        return list(self.db.scalars(stmt).all())

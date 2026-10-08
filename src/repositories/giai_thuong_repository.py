from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.giai_thuong import GiaiThuong
from src.repositories.giai_thuong_repository_interface import GiaiThuongRepositoryInterface


class GiaiThuongRepository(GiaiThuongRepositoryInterface):
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, record: GiaiThuong) -> GiaiThuong:
        self.db.add(record)
        self.db.flush()
        self.db.refresh(record)
        return record

    def list_by_cccd(self, cccd: str) -> list[GiaiThuong]:
        stmt = select(GiaiThuong).where(GiaiThuong.cccd == cccd)
        return list(self.db.scalars(stmt).all())

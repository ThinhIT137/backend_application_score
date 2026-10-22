from abc import ABC, abstractmethod

from src.models.giai_thuong import GiaiThuong


class GiaiThuongRepositoryInterface(ABC):
    @abstractmethod
    def create(self, record: GiaiThuong) -> GiaiThuong:
        raise NotImplementedError

    @abstractmethod
    def list_by_cccd(self, cccd: str) -> list[GiaiThuong]:
        raise NotImplementedError

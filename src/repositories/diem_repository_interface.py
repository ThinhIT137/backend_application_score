from abc import ABC, abstractmethod

from src.models.diem_thi_sinh import BangDiem, ChungChi
from src.models.tham_chieu import LoTrinhTuyenSinh
from src.schemas.diem_schema import DiemMonThpt


class DiemRepositoryInterface(ABC):
    @abstractmethod
    def thi_sinh_exists(self, cccd: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def mon_exists(self, ma_mon: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_bang_diem_tnthpt(self, cccd: str, nam_hoc: int) -> BangDiem | None:
        raise NotImplementedError

    @abstractmethod
    def upsert_bang_diem_tnthpt(self, cccd: str, nam_hoc: int, diem_mon: list[DiemMonThpt]) -> BangDiem:
        raise NotImplementedError

    @abstractmethod
    def list_lo_trinh(self, nam_tuyen_sinh: int) -> list[LoTrinhTuyenSinh]:
        raise NotImplementedError

    @abstractmethod
    def find_dgnl_trung(self, cccd: str, nam: int) -> ChungChi | None:
        raise NotImplementedError

    @abstractmethod
    def create_chung_chi(self, chung_chi: ChungChi) -> ChungChi:
        raise NotImplementedError

    @abstractmethod
    def list_dgnl_cho(self) -> list[ChungChi]:
        raise NotImplementedError

    @abstractmethod
    def get_chung_chi(self, ma_chung_chi: str) -> ChungChi | None:
        raise NotImplementedError

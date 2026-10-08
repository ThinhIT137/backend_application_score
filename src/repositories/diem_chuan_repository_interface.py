from abc import ABC, abstractmethod

from src.models.diem_chuan import DiemTrungTuyen, LichSuDiemChuan


class DiemChuanRepositoryInterface(ABC):
    @abstractmethod
    def list_all(self, ma_chuong_trinh: str | None = None, nam: int | None = None) -> list[LichSuDiemChuan]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, ma_ls_dc: str) -> LichSuDiemChuan | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_chuong_trinh_nam(self, ma_chuong_trinh: str, nam: int) -> LichSuDiemChuan | None:
        raise NotImplementedError

    @abstractmethod
    def create(self, record: LichSuDiemChuan) -> LichSuDiemChuan:
        raise NotImplementedError

    @abstractmethod
    def update(self, record: LichSuDiemChuan) -> LichSuDiemChuan:
        raise NotImplementedError

    @abstractmethod
    def delete(self, ma_ls_dc: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_diem_trung_tuyen(self, dtt: DiemTrungTuyen) -> DiemTrungTuyen:
        raise NotImplementedError

    @abstractmethod
    def list_diem_trung_tuyen_by_ls(
        self, ma_ls_dc: str, nam: int | None = None
    ) -> list[DiemTrungTuyen]:
        raise NotImplementedError

from abc import ABC, abstractmethod

from src.models.diem_chuan import DiemTrungTuyen, LichSuDiemChuan
from src.schemas.diem_chuan_schema import (
    SuaDiemChuanRequest,
    TaoDiemChuanRequest,
    ThemDiemTrungTuyenRequest,
)
from src.schemas.quy_doi_schema import QuyDoiRequest, QuyDoiResponse


class DiemChuanServiceInterface(ABC):
    @abstractmethod
    def list_diem_chuan(
        self, ma_chuong_trinh: str | None = None, nam: int | None = None
    ) -> list[LichSuDiemChuan]:
        raise NotImplementedError

    @abstractmethod
    def get_diem_chuan(self, ma_ls_dc: str) -> LichSuDiemChuan:
        raise NotImplementedError

    @abstractmethod
    def tao_diem_chuan(self, payload: TaoDiemChuanRequest, ma_admin: str) -> LichSuDiemChuan:
        raise NotImplementedError

    @abstractmethod
    def sua_diem_chuan(self, ma_ls_dc: str, payload: SuaDiemChuanRequest) -> LichSuDiemChuan:
        raise NotImplementedError

    @abstractmethod
    def xoa_diem_chuan(self, ma_ls_dc: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def them_diem_trung_tuyen(
        self, ma_ls_dc: str, payload: ThemDiemTrungTuyenRequest
    ) -> DiemTrungTuyen:
        raise NotImplementedError

    @abstractmethod
    def tinh_diem_quy_doi(self, payload: QuyDoiRequest) -> QuyDoiResponse:
        raise NotImplementedError

from abc import ABC, abstractmethod

from src.core.security import CurrentUser
from src.models.diem_thi_sinh import ChungChi
from src.schemas.diem_schema import (
    ChungChiDgnlItem,
    DongBoThptRequest,
    DongBoThptResponse,
    NopDgnlRequest,
)


class DiemServiceInterface(ABC):
    @abstractmethod
    def dong_bo_thpt(self, payload: DongBoThptRequest) -> DongBoThptResponse:
        raise NotImplementedError

    @abstractmethod
    def nop_dgnl(self, payload: NopDgnlRequest, user: CurrentUser | None = None) -> ChungChiDgnlItem:
        raise NotImplementedError

    @abstractmethod
    def list_dgnl_cho(self) -> list[ChungChi]:
        raise NotImplementedError

    @abstractmethod
    def xac_nhan_dgnl(self, ma_chung_chi: str) -> ChungChi:
        raise NotImplementedError

    @abstractmethod
    def yeu_cau_bo_sung(self, ma_chung_chi: str) -> ChungChi:
        raise NotImplementedError

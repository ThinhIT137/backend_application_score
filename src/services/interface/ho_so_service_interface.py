from abc import ABC, abstractmethod

from src.core.security import CurrentUser
from src.models.ho_so import NguyenVongSinhVien
from src.models.trang_thai_ho_so import TrangThaiDuyet
from src.schemas.ho_so_schema import (
    CongBoKetQuaRequest,
    CongBoKetQuaResponse,
    HoSoDetail,
    NopHoSoRequest,
)


class HoSoServiceInterface(ABC):
    @abstractmethod
    def list_ho_so(
        self,
        *,
        trang_thai: TrangThaiDuyet | None,
        nam_tuyen_sinh: int | None,
        ma_chuong_trinh: str | None,
    ) -> list[NguyenVongSinhVien]:
        raise NotImplementedError

    @abstractmethod
    def get_detail(self, ma_ho_so: str) -> HoSoDetail:
        raise NotImplementedError

    @abstractmethod
    def duyet(self, ma_ho_so: str, admin: CurrentUser) -> NguyenVongSinhVien:
        raise NotImplementedError

    @abstractmethod
    def tu_choi(self, ma_ho_so: str, ly_do: str, admin: CurrentUser) -> NguyenVongSinhVien:
        raise NotImplementedError

    @abstractmethod
    def cong_bo_ket_qua(self, payload: CongBoKetQuaRequest) -> CongBoKetQuaResponse:
        raise NotImplementedError

    # --- Sprint 1 methods ---

    @abstractmethod
    def nop_ho_so(self, payload: NopHoSoRequest) -> NguyenVongSinhVien:
        raise NotImplementedError

    @abstractmethod
    def tra_cuu(
        self,
        ma_ho_so: str | None = None,
        cccd: str | None = None,
        nam_tuyen_sinh: int | None = None,
    ) -> list[NguyenVongSinhVien]:
        raise NotImplementedError

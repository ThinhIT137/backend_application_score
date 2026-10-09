from abc import ABC, abstractmethod

from src.core.security import CurrentUser
from src.models.ho_so import NguyenVongSinhVien
from src.models.trang_thai_ho_so import TrangThaiDuyet
from src.schemas.ho_so_schema import CongBoKetQuaRequest, CongBoKetQuaResponse, HoSoDetail


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
    def get_own_detail(self, ma_ho_so: str, user: CurrentUser) -> HoSoDetail:
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

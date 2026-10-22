from abc import ABC, abstractmethod

from src.models.diem_thi_sinh import BangDiem, ChungChi
from src.models.giai_thuong import GiaiThuong
from src.models.ho_so import NguyenVongSinhVien
from src.models.trang_thai_ho_so import TrangThaiDuyet


class HoSoRepositoryInterface(ABC):
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
    def get_by_ma_ho_so(self, ma_ho_so: str) -> NguyenVongSinhVien | None:
        raise NotImplementedError

    @abstractmethod
    def list_chung_chi_by_cccd(self, cccd: str) -> list[ChungChi]:
        raise NotImplementedError

    @abstractmethod
    def list_giai_thuong_by_cccd(self, cccd: str) -> list[GiaiThuong]:
        raise NotImplementedError

    @abstractmethod
    def list_bang_diem_by_cccd(self, cccd: str) -> list[BangDiem]:
        raise NotImplementedError

    @abstractmethod
    def count_cho(
        self,
        *,
        nam_tuyen_sinh: int,
        ma_chuong_trinh: str | None,
        ma_phuong_thuc: str | None,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    def list_for_cong_bo(
        self,
        *,
        nam_tuyen_sinh: int,
        ma_chuong_trinh: str | None,
        ma_phuong_thuc: str | None,
    ) -> list[NguyenVongSinhVien]:
        raise NotImplementedError

    # --- Sprint 1 methods ---

    @abstractmethod
    def create_ho_so(self, record: NguyenVongSinhVien) -> NguyenVongSinhVien:
        raise NotImplementedError

    @abstractmethod
    def find_by_cccd_nam_phuong_thuc(
        self, cccd: str, nam: int, ma_phuong_thuc: str
    ) -> NguyenVongSinhVien | None:
        raise NotImplementedError

    @abstractmethod
    def find_by_cccd(
        self, cccd: str, nam: int | None = None
    ) -> list[NguyenVongSinhVien]:
        raise NotImplementedError

    @abstractmethod
    def check_thi_sinh_exists(self, cccd: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def create_chung_chi(self, record: ChungChi) -> ChungChi:
        raise NotImplementedError

    @abstractmethod
    def create_giai_thuong(self, record: GiaiThuong) -> GiaiThuong:
        raise NotImplementedError

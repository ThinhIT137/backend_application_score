from abc import ABC, abstractmethod

from src.schemas.diem_schema import ThiSinhDiemThpt


class ExternalScoreProvider(ABC):
    """Nguồn điểm THPT (Bộ GD&ĐT). Triển khai mock khi chưa có API thật."""

    @abstractmethod
    def fetch_thpt_scores(self, nam_hoc: int) -> list[ThiSinhDiemThpt]:
        raise NotImplementedError


class ExternalDgnlProvider(ABC):
    """Nguồn đối soát ĐGNL (ĐHQG)."""

    @abstractmethod
    def diem_khop(self, cccd: str, diem: str | None) -> bool:
        raise NotImplementedError

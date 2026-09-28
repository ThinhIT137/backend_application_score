from src.schemas.diem_schema import ThiSinhDiemThpt
from src.services.adapters.score_provider import ExternalDgnlProvider, ExternalScoreProvider


class MockBoGddtProvider(ExternalScoreProvider):
    def fetch_thpt_scores(self, nam_hoc: int) -> list[ThiSinhDiemThpt]:
        _ = nam_hoc
        return []


class MockDhqgDgnlProvider(ExternalDgnlProvider):
    def diem_khop(self, cccd: str, diem: str | None) -> bool:
        _ = cccd
        return diem is not None and diem.strip() != ""

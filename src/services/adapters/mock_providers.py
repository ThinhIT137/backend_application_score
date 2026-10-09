"""Deterministic synthetic providers, bundled within this microservice."""
import json
import math
from pathlib import Path
from src.schemas.diem_schema import ThiSinhDiemThpt
from src.services.adapters.score_provider import ExternalDgnlProvider, ExternalScoreProvider

MOCK_PATH = Path(__file__).resolve().parents[2] / "data" / "mock_scores.json"

def load_mock_scores():
    with MOCK_PATH.open(encoding="utf-8") as stream:
        return json.load(stream)

class MockBoGddtProvider(ExternalScoreProvider):
    def fetch_thpt_scores(self, nam_hoc):
        return [ThiSinhDiemThpt.model_validate(r)
                for r in load_mock_scores()["thpt"].get(str(nam_hoc), [])]

class MockDhqgDgnlProvider(ExternalDgnlProvider):
    def diem_khop(self, cccd, diem, nam=None):
        # A nonempty score is insufficient: compare candidate, year and numeric value.
        if nam is None:
            return False
        expected = load_mock_scores()["dgnl"].get(cccd, {}).get(str(nam))
        try:
            value = float(diem)
        except (TypeError, ValueError):
            return False
        return expected is not None and math.isfinite(value) and value == expected

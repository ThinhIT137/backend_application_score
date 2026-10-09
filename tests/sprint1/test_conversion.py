"""Real local asset tests; no database, network or AI microservice required."""
import math
from pathlib import Path
import pytest
from src.core.exceptions import DuLieuKhongHopLe
from src.services.conversion_service import load_conversion_scales, convert_to_thpt

METHODS = ("hoc_ba", "hsa", "tsa")
ROWS = [(method, row) for method in METHODS
        for row in load_conversion_scales()[f"{method}_to_thpt"]]


@pytest.mark.parametrize("method,row", ROWS)
@pytest.mark.parametrize("position", [0, 0.5, 1])
def test_interval_endpoints_and_midpoint(method, row, position):
    # Check every interval against the stored endpoints, including shared bounds.
    score = row[f"{method}_min"] + position * (row[f"{method}_max"] - row[f"{method}_min"])
    expected = row["thpt_min"] + position * (row["thpt_max"] - row["thpt_min"])
    assert convert_to_thpt(method, score) == pytest.approx(expected)


@pytest.mark.parametrize("method", METHODS)
def test_reject_out_of_table(method):
    rows = load_conversion_scales()[f"{method}_to_thpt"]
    for score in (min(r[f"{method}_min"] for r in rows) - 0.01,
                  max(r[f"{method}_max"] for r in rows) + 0.01):
        with pytest.raises(DuLieuKhongHopLe):
            convert_to_thpt(method, score)


@pytest.mark.parametrize("score", [math.nan, math.inf, -math.inf])
def test_reject_nonfinite(score):
    with pytest.raises(DuLieuKhongHopLe):
        convert_to_thpt("hoc_ba", score)


@pytest.mark.parametrize("method,year", [("ielts", 2026), ("award", 2026), ("hoc_ba", 2025)])
def test_reject_unsupported_rules(method, year):
    with pytest.raises(DuLieuKhongHopLe):
        convert_to_thpt(method, 25, year)


def test_load_independent_of_working_directory(monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parent)
    assert convert_to_thpt("hoc_ba", 30) == 30
    assert len(load_conversion_scales()["tsa_to_thpt"]) == 9


@pytest.fixture
def conversion_client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from src.router.diem_router import router
    from src.core.exceptions import register_exception_handlers
    from src.core.security import get_current_user, CurrentUser
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(role="thi_sinh", cccd="001")
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_conversion_api_success(conversion_client):
    response = conversion_client.post("/diem/quy-doi", json={"phuong_thuc": "hoc_ba", "diem": 29.9})
    assert response.status_code == 200
    assert response.json()["diem_thpt"] == pytest.approx(29.1)


@pytest.mark.parametrize("payload,status", [
    ({"phuong_thuc": "ielts", "diem": 7}, 422),
    ({"phuong_thuc": "hoc_ba"}, 422),
    ({"phuong_thuc": "hoc_ba", "diem": 25, "nam_tuyen_sinh": 2025}, 422),
    ({"phuong_thuc": "hoc_ba", "diem": 20}, 400),
])
def test_conversion_api_validation(conversion_client, payload, status):
    assert conversion_client.post("/diem/quy-doi", json=payload).status_code == status


def test_conversion_api_requires_auth(conversion_client):
    conversion_client.app.dependency_overrides.clear()
    response = conversion_client.post("/diem/quy-doi", json={"phuong_thuc": "hoc_ba", "diem": 25})
    assert response.status_code == 401

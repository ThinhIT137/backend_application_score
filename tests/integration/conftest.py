"""API + signed JWT + real repositories + transaction-enabled SQLite.
No production settings, DB or secrets are accessed.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.core import database, security
from src.core.config import Settings
from src.models.admission import ChuongTrinhDaoTao, PhuongThucXetTuyen, ToHopXetTuyen
from src.models.tham_chieu import ThiSinh, Admin, DanhMucMonHoc, LoTrinhTuyenSinh
from app import app

@pytest.fixture
def api(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
    database.Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(database, "get_engine", lambda: engine)
    monkeypatch.setattr(database, "SessionLocal", sessions)
    settings = Settings(_env_file=None, database_url="sqlite://", jwt_secret="public-test-only-key-32-characters")
    monkeypatch.setattr(security, "get_settings", lambda: settings)
    import src.router.diem_router as scores
    monkeypatch.setattr(scores, "get_settings", lambda: settings)
    with sessions.begin() as db:
        db.add_all([Admin(ma_admin="A1"), ThiSinh(cccd="000000000001"), ThiSinh(cccd="000000000002"),
            ChuongTrinhDaoTao(ma_chuong_trinh="P1"), PhuongThucXetTuyen(ma_phuong_thuc="HB"),
            PhuongThucXetTuyen(ma_phuong_thuc="CC"), PhuongThucXetTuyen(ma_phuong_thuc="GT"),
            ToHopXetTuyen(ma_to_hop="A00"), DanhMucMonHoc(ma_mon="TOAN"), DanhMucMonHoc(ma_mon="VAN")])
        db.flush()
        now = datetime.now()
        db.add(LoTrinhTuyenSinh(ma_su_kien="EVENT", ten_su_kien="cong_bo ket qua",
            ma_admin_cap_nhat="A1", thoi_gian_bat_dau=now-timedelta(days=1), thoi_gian_ket_thuc=now+timedelta(days=1)))
    def token(role="thi_sinh", sub="000000000001", key=None, expired=False):
        payload = {"role": role, "sub": sub,
            "exp": datetime.now(timezone.utc)+timedelta(minutes=-1 if expired else 10)}
        return {"Authorization": "Bearer " + jwt.encode(payload, key or settings.jwt_secret, algorithm="HS256")}
    app.dependency_overrides.clear()
    with TestClient(app) as client:
        yield SimpleNamespace(client=client, db=sessions, token=token,
            student=token(), other=token(sub="000000000002"), admin=token("admin", "A1"))
    app.dependency_overrides.clear()
    engine.dispose()

@pytest.fixture
def submission():
    return {"ma_chuong_trinh": "P1", "ma_phuong_thuc": "HB", "ma_to_hop": "A00",
        "nguyen_vong": 1, "nam_tuyen_sinh": 2026,
        "bang_diem": [{"loai_diem": "lop_12", "nam_hoc": 2026,
            "diem_mon": [{"ma_mon": "TOAN", "diem_so": 9}]}]}

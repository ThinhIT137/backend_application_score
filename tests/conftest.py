import sys
import os
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime
from unittest.mock import Mock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "backend-tests-only-not-for-deployment"
os.environ["JWT_ACCESSTOKEN"] = "backend-tests-only-not-for-deployment"
os.environ["EMAIL_PROVIDER"] = "mock"
os.environ["CORS_ALLOWED_ORIGINS"] = '["http://localhost:3000","http://127.0.0.1:3000"]'
from src.core.config import get_settings
from src.core import database
from src import models
import src.models.admission

get_settings.cache_clear()

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
database.Base.metadata.create_all(test_engine)
database._engine = test_engine
database.SessionLocal.configure(bind=test_engine, expire_on_commit=False)

from src.services.ho_so_service import HoSoService
from src.services.diem_service import DiemService
from src.models.trang_thai_ho_so import TrangThaiDuyet, NguonDuLieu

@pytest.fixture
def record():
    # D? li?u ?? schema, kh?ng ghi DB th?t.
    return SimpleNamespace(ma_ho_so="H1", cccd="001", ma_chuong_trinh="P1",
        trang_thai=TrangThaiDuyet.cho, ket_qua=None, ma_phuong_thuc="PT1",
        nguon_du_lieu=NguonDuLieu.tu_nop, nguyen_vong=1, nam_tuyen_sinh=2026,
        ma_admin_xu_ly=None, create_at=datetime(2026,1,1),
        diem_uu_tien_ap_dung=None, tong_diem_xet_tuyen=None, ma_to_hop=None)

@pytest.fixture
def profile(record):
    repo, scores, notify = Mock(), Mock(), Mock()
    repo.get_by_ma_ho_so.return_value = record
    for name in ("list_chung_chi_by_cccd", "list_giai_thuong_by_cccd", "list_bang_diem_by_cccd"):
        getattr(repo,name).return_value = []
    return HoSoService(repo,scores,notify),repo,scores,notify

@pytest.fixture
def scoring():
    repo,thpt,dgnl=Mock(),Mock(),Mock()
    repo.thi_sinh_exists.return_value=True
    repo.mon_exists.return_value=True
    repo.find_dgnl_trung.return_value=None
    repo.create_chung_chi.side_effect=lambda item:item
    return DiemService(repo,thpt,dgnl),repo,thpt,dgnl

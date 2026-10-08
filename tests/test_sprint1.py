import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from jose import jwt

from src.app import app
from src.core.config import get_settings
from src.core.exceptions import DuLieuKhongHopLe, HoSoNotFound
from src.models.diem_chuan import DiemTrungTuyen, LichSuDiemChuan
from src.models.ho_so import NguyenVongSinhVien
from src.models.trang_thai_ho_so import TrangThaiDuyet
from src.repositories.diem_chuan_repository_interface import DiemChuanRepositoryInterface
from src.repositories.ho_so_repository_interface import HoSoRepositoryInterface
from src.schemas.diem_chuan_schema import (
    SuaDiemChuanRequest,
    TaoDiemChuanRequest,
    ThemDiemTrungTuyenRequest,
)
from src.schemas.ho_so_schema import (
    NopChungChiItem,
    NopGiaiThuongItem,
    NopHoSoRequest,
)
from src.schemas.quy_doi_schema import (
    DiemChungChiInput,
    DiemThptInput,
    QuyDoiRequest,
)
from src.services.adapters.notification import NoOpNotificationPublisher
from src.services.diem_chuan_service import DiemChuanService
from src.services.ho_so_service import HoSoService

client = TestClient(app)
settings = get_settings()


def create_token(payload: dict) -> str:
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# ---------------------------------------------------------------------------
# Feature 2: Tinh diem quy doi (API & Service)
# ---------------------------------------------------------------------------


def test_api_tinh_diem_quy_doi_no_auth_needed():
    """POST /diem/quy-doi khong yeu cau dang nhap, tinh toan stateless."""
    payload = {
        "diem_thpt": [
            {"ma_mon": "toan", "diem": 9.0},
            {"ma_mon": "vat_ly", "diem": 8.5},
            {"ma_mon": "hoa_hoc", "diem": 8.0},
        ],
        "chung_chi": [
            {"loai": "IELTS", "diem": 7.5},
            {"loai": "SAT", "diem": 1400.0},
        ],
        "doi_tuong_uu_tien": "KV1",
    }
    resp = client.post("/diem/quy-doi", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["diem_uu_tien"] == 0.75
    assert len(data["chi_tiet"]) >= 3
    # Diem THPT: 9.0 + 8.5 + 8.0 = 25.5 + 0.75 = 26.25
    pt_thpt = next(p for p in data["chi_tiet"] if p["ma_phuong_thuc"] == "PT100")
    assert pt_thpt["diem_quy_doi"] == 26.25
    assert data["phuong_thuc_tot_nhat"] is not None


def test_tinh_diem_quy_doi_canh_bao():
    """Canh bao diem vuot ngoai dai hop le."""
    mock_repo = MagicMock(spec=DiemChuanRepositoryInterface)
    service = DiemChuanService(mock_repo)

    req = QuyDoiRequest(
        diem_thpt=[DiemThptInput(ma_mon="toan", diem=10.5)],  # vuot qua 10.0
        chung_chi=[DiemChungChiInput(loai="IELTS", diem=10.0)],  # IELTS toi da 9.0
    )
    res = service.tinh_diem_quy_doi(req)
    assert len(res.canh_bao) >= 2


# ---------------------------------------------------------------------------
# Feature 1: Quan ly diem chuan (Admin API Auth & Service CRUD)
# ---------------------------------------------------------------------------


def test_diem_chuan_requires_admin():
    """Cac endpoint /diem-chuan deu can quyen admin."""
    # Khong truyen token -> 401
    resp = client.get("/diem-chuan")
    assert resp.status_code == 401

    # Thi sinh -> 403
    st_token = create_token({"role": "thi_sinh", "cccd": "123456789012"})
    resp = client.get("/diem-chuan", headers={"Authorization": f"Bearer {st_token}"})
    assert resp.status_code == 403

    # Admin -> duoc phep goi
    adm_token = create_token({"role": "super_admin", "ma_admin": "adm-001"})
    resp = client.get("/diem-chuan", headers={"Authorization": f"Bearer {adm_token}"})
    assert resp.status_code in {200, 500}


def test_service_crud_diem_chuan():
    """Unit test service CRUD LichSuDiemChuan."""
    mock_repo = MagicMock(spec=DiemChuanRepositoryInterface)
    service = DiemChuanService(mock_repo)

    # 1. Tao moi
    mock_repo.get_by_chuong_trinh_nam.return_value = None
    mock_repo.create.side_effect = lambda rec: rec

    tao_req = TaoDiemChuanRequest(
        ma_ls_dc="ls-001",
        ma_chuong_trinh="CNTT",
        nam=2025,
        chi_tieu=150,
    )
    created = service.tao_diem_chuan(tao_req, ma_admin="adm-001")
    assert created.ma_ls_dc == "ls-001"
    assert created.chi_tieu == 150

    # 2. Check trung lap
    mock_repo.get_by_chuong_trinh_nam.return_value = created
    with pytest.raises(DuLieuKhongHopLe):
        service.tao_diem_chuan(tao_req, ma_admin="adm-001")

    # 3. Sua
    mock_repo.get_by_id.return_value = created
    mock_repo.update.side_effect = lambda rec: rec
    updated = service.sua_diem_chuan("ls-001", SuaDiemChuanRequest(chi_tieu=200, trung_tuyen=180))
    assert updated.chi_tieu == 200
    assert updated.trung_tuyen == 180

    # 4. Them diem trung tuyen
    mock_repo.list_diem_trung_tuyen_by_ls.return_value = []
    mock_repo.add_diem_trung_tuyen.side_effect = lambda dtt: dtt
    dtt_req = ThemDiemTrungTuyenRequest(
        ma_diem_tt="dtt-001",
        ma_phuong_thuc="PT100",
        diem=27.5,
    )
    dtt = service.them_diem_trung_tuyen("ls-001", dtt_req)
    assert dtt.diem == 27.5


# ---------------------------------------------------------------------------
# Feature 3 & 4: Nop ho so & Tra cuu (API & Service)
# ---------------------------------------------------------------------------


def test_api_tra_cuu_validation():
    """GET /ho-so/tra-cuu: thieu ca ma_ho_so va cccd phai bao 400."""
    resp = client.get("/ho-so/tra-cuu")
    assert resp.status_code == 400


def test_service_nop_ho_so_and_tra_cuu():
    """Unit test service nop ho so va tra cuu."""
    mock_repo = MagicMock(spec=HoSoRepositoryInterface)
    mock_diem_repo = MagicMock()
    service = HoSoService(mock_repo, mock_diem_repo, NoOpNotificationPublisher())

    # 1. Nop ho so khi thi sinh khong ton tai
    mock_repo.check_thi_sinh_exists.return_value = False
    req = NopHoSoRequest(
        cccd="012345678901",
        ma_chuong_trinh="CNTT",
        ma_phuong_thuc="PT100",
        nam_tuyen_sinh=2025,
    )
    with pytest.raises(DuLieuKhongHopLe) as exc_info:
        service.nop_ho_so(req)
    assert "Không tìm thấy thí sinh" in str(exc_info.value)

    # 2. Nop ho so thanh cong
    mock_repo.check_thi_sinh_exists.return_value = True
    mock_repo.find_by_cccd_nam_phuong_thuc.return_value = None
    mock_repo.create_ho_so.side_effect = lambda rec: rec

    req_with_attachments = NopHoSoRequest(
        cccd="012345678901",
        ma_chuong_trinh="CNTT",
        ma_phuong_thuc="PT409",
        nam_tuyen_sinh=2025,
        chung_chi=[
            NopChungChiItem(loai_chung_chi="IELTS", diem_hoac_hang="7.5", file_dinh_kem="mc.pdf")
        ],
        giai_thuong=[
            NopGiaiThuongItem(giai_thuong="giai_nhat", loai_giai_thuong="toan_quoc", mon_hoc="toan")
        ],
    )
    created_hs = service.nop_ho_so(req_with_attachments)
    assert created_hs.trang_thai == TrangThaiDuyet.cho
    assert created_hs.ma_ho_so.startswith("HS-")
    assert mock_repo.create_chung_chi.call_count == 1
    assert mock_repo.create_giai_thuong.call_count == 1

    # 3. Chống nộp trùng
    mock_repo.find_by_cccd_nam_phuong_thuc.return_value = created_hs
    with pytest.raises(DuLieuKhongHopLe) as exc_dup:
        service.nop_ho_so(req_with_attachments)
    assert "đã nộp hồ sơ" in str(exc_dup.value)

    # 4. Tra cuu thanh cong theo ma_ho_so
    mock_repo.get_by_ma_ho_so.return_value = created_hs
    res = service.tra_cuu(ma_ho_so=created_hs.ma_ho_so)
    assert len(res) == 1
    assert res[0].ma_ho_so == created_hs.ma_ho_so

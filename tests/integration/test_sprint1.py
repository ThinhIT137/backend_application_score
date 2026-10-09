"""Sprint 1: execute HTTP, JWT and persistence together, not mocked services."""
from copy import deepcopy
import pytest
from sqlalchemy import select, func, event
from src.models.admission import LichSuDiemChuan, DiemTrungTuyen
from src.models.ho_so import NguyenVongSinhVien
from src.models.diem_chuan import BangDiem, DiemChiTiet, ChungChi
from src.models.tham_chieu import GiaiThuong

def cutoff():
    return {"ma_chuong_trinh": "P1", "nam": 2025, "chi_tieu": 100,
        "diem_trung_tuyen": [{"ma_phuong_thuc": "HB", "diem": 26.5}]}

def test_cutoff_full_crud(api):
    response = api.client.post("/diem-chuan", json=cutoff(), headers=api.admin)
    assert response.status_code == 201, response.text
    key = response.json()["ma_ls_dc"]
    assert response.json()["ma_admin_cap_nhat"] == "A1"
    assert api.client.get(f"/diem-chuan/{key}", headers=api.admin).json()["diem_trung_tuyen"][0]["diem"] == 26.5
    assert len(api.client.get("/diem-chuan?nam=2025&ma_chuong_trinh=P1", headers=api.admin).json()) == 1
    assert api.client.get("/diem-chuan?nam=2024", headers=api.admin).json() == []
    data = cutoff()
    data["diem_trung_tuyen"][0]["diem"] = 27.0
    response = api.client.put(f"/diem-chuan/{key}", json=data, headers=api.admin)
    assert response.status_code == 200, response.text
    with api.db() as db:
        assert db.scalar(select(DiemTrungTuyen.diem)) == 27.0
        assert db.scalar(select(func.count()).select_from(DiemTrungTuyen)) == 1
    assert api.client.delete(f"/diem-chuan/{key}", headers=api.admin).status_code == 204
    assert api.client.get(f"/diem-chuan/{key}", headers=api.admin).status_code == 404
    with api.db() as db:
        assert db.scalar(select(func.count()).select_from(DiemTrungTuyen)) == 0

def test_cutoff_duplicate_and_missing(api):
    assert api.client.post("/diem-chuan", json=cutoff(), headers=api.admin).status_code == 201
    assert api.client.post("/diem-chuan", json=cutoff(), headers=api.admin).status_code == 409
    assert api.client.put("/diem-chuan/missing", json={**cutoff(), "nam": 2024}, headers=api.admin).status_code == 404
    assert api.client.delete("/diem-chuan/missing", headers=api.admin).status_code == 404

@pytest.mark.parametrize("change,status", [
    ({"ma_chuong_trinh": "missing"}, 400), ({"chi_tieu": -1}, 422),
    ({"diem_trung_tuyen": []}, 422),
    ({"diem_trung_tuyen": [{"ma_phuong_thuc": "missing", "diem": 20}]}, 400),
    ({"diem_trung_tuyen": [{"ma_phuong_thuc": "HB", "diem": -1}]}, 422),
    ({"diem_trung_tuyen": [{"ma_phuong_thuc": "HB", "diem": 20}]*2}, 422),
])
def test_cutoff_validation(api, change, status):
    assert api.client.post("/diem-chuan", json={**cutoff(), **change}, headers=api.admin).status_code == status
    with api.db() as db:
        assert db.scalar(select(func.count()).select_from(LichSuDiemChuan)) == 0

@pytest.mark.parametrize("method,path", [("get", "/diem-chuan"), ("post", "/diem-chuan"),
    ("put", "/diem-chuan/missing"), ("delete", "/diem-chuan/missing")])
def test_cutoff_denies_candidate(api, method, path):
    options = {"headers": api.student}
    if method in ("post", "put"):
        options["json"] = cutoff()
    assert getattr(api.client, method)(path, **options).status_code == 403

@pytest.mark.parametrize("kind", ["bang_diem", "chung_chi", "giai_thuong"])
def test_submit_each_evidence_and_read_ownership(api, submission, kind):
    data = deepcopy(submission)
    data.pop("bang_diem")
    data[kind] = {
        "bang_diem": submission["bang_diem"],
        "chung_chi": [{"loai_chung_chi": "IELTS", "diem_hoac_hang": "7.0", "file_dinh_kem": "cert.pdf"}],
        "giai_thuong": [{"giai_thuong": "giai_nhi", "loai_giai_thuong": "toan_quoc", "mon_hoc": "toan"}],
    }[kind]
    response = api.client.post("/ho-so", json=data, headers=api.student)
    assert response.status_code == 201, response.text
    key = response.json()["ma_ho_so"]
    assert response.json()["cccd"] == "000000000001"
    response = api.client.get(f"/ho-so/cua-toi/{key}", headers=api.student)
    assert response.status_code == 200, response.text
    assert len(response.json()[kind]) == 1
    assert response.json()["trang_thai"] == "cho"
    if kind == "bang_diem":
        assert response.json()[kind][0]["chi_tiet"][0]["diem_so"] == 9
    assert api.client.get(f"/ho-so/cua-toi/{key}", headers=api.other).status_code == 404
    assert api.client.get(f"/ho-so/{key}", headers=api.student).status_code == 403
    assert api.client.get(f"/ho-so/{key}", headers=api.admin).status_code == 200
    assert api.client.post("/ho-so", json=data, headers=api.student).status_code == 409

@pytest.mark.parametrize("change,status", [
    ({"bang_diem": []}, 422), ({"cccd": "000000000002"}, 422),
    ({"ma_chuong_trinh": "missing"}, 400), ({"ma_phuong_thuc": "missing"}, 400),
    ({"ma_to_hop": "missing"}, 400), ({"nguyen_vong": 0}, 422),
    ({"bang_diem": [{"loai_diem": "lop_12", "nam_hoc": 2026, "diem_mon": [{"ma_mon": "TOAN", "diem_so": 11}]}]}, 422),
    ({"bang_diem": [{"loai_diem": "lop_12", "nam_hoc": 2026, "diem_mon": [{"ma_mon": "missing", "diem_so": 8}]}]}, 400),
    ({"chung_chi": [{"loai_chung_chi": "IELTS", "diem_hoac_hang": "7", "file_dinh_kem": "x.exe"}]}, 400),
    ({"giai_thuong": [{"giai_thuong": "invalid", "loai_giai_thuong": "tinh", "mon_hoc": "toan"}]}, 422),
])
def test_submission_validation_no_persistence(api, submission, change, status):
    response = api.client.post("/ho-so", json={**submission, **change}, headers=api.student)
    assert response.status_code == status, response.text
    with api.db() as db:
        assert db.scalar(select(func.count()).select_from(NguyenVongSinhVien)) == 0

@pytest.mark.parametrize("auth", ["none", "expired", "wrong_key", "admin", "unknown_candidate"])
def test_submission_auth(api, submission, auth):
    headers = {"none": {}, "expired": api.token(expired=True),
        "wrong_key": api.token(key="wrong-key"), "admin": api.admin,
        "unknown_candidate": api.token(sub="999999999999")}[auth]
    expected = {"none": 401, "expired": 401, "wrong_key": 401, "admin": 403, "unknown_candidate": 400}[auth]
    assert api.client.post("/ho-so", json=submission, headers=headers).status_code == expected

def test_submission_rolls_back_on_mid_transaction_failure(api, submission):
    # Inject a DB failure after dossier insert; verify the request transaction rolls back.
    def fail(_mapper, _connection, _target):
        raise RuntimeError("injected DB failure")
    event.listen(DiemChiTiet, "before_insert", fail)
    try:
        with pytest.raises(RuntimeError, match="injected DB failure"):
            api.client.post("/ho-so", json=submission, headers=api.student)
    finally:
        event.remove(DiemChiTiet, "before_insert", fail)
    with api.db() as db:
        for model in (NguyenVongSinhVien, BangDiem, DiemChiTiet):
            assert db.scalar(select(func.count()).select_from(model)) == 0


def test_combined_evidence_persists_atomically(api, submission):
    submission["chung_chi"] = [{"loai_chung_chi": "IELTS", "diem_hoac_hang": "7", "file_dinh_kem": "e.pdf"}]
    submission["giai_thuong"] = [{"giai_thuong": "giai_nhat", "loai_giai_thuong": "tinh", "mon_hoc": "toan"}]
    r = api.client.post("/ho-so", json=submission, headers=api.student)
    assert r.status_code == 201, r.text
    with api.db() as db:
        for model in (NguyenVongSinhVien, BangDiem, ChungChi, GiaiThuong):
            assert db.scalar(select(func.count()).select_from(model)) == 1

def test_cutoff_update_duplicate_and_foreign_reference_keeps_original(api):
    first = api.client.post("/diem-chuan", json=cutoff(), headers=api.admin).json()["ma_ls_dc"]
    second = api.client.post("/diem-chuan", json={**cutoff(), "nam": 2024}, headers=api.admin).json()["ma_ls_dc"]
    assert api.client.put(f"/diem-chuan/{second}", json=cutoff(), headers=api.admin).status_code == 409
    assert api.client.put(f"/diem-chuan/{first}", json={**cutoff(), "ma_chuong_trinh": "missing"}, headers=api.admin).status_code == 400
    assert api.client.get(f"/diem-chuan/{second}", headers=api.admin).json()["nam"] == 2024

def test_lookup_missing_and_unauthenticated(api):
    assert api.client.get("/ho-so/cua-toi/missing", headers=api.student).status_code == 404
    assert api.client.get("/ho-so/cua-toi/missing").status_code == 401

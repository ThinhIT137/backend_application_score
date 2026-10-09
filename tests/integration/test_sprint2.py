"""Sprint 2 runs real repositories and the bundled synthetic examination source."""
from datetime import datetime, timedelta
import pytest
from sqlalchemy import select, func
from src.models.ho_so import NguyenVongSinhVien
from src.models.diem_chuan import BangDiem, DiemChiTiet, ChungChi
from src.models.tham_chieu import LoTrinhTuyenSinh
from src.services.adapters.mock_providers import MockBoGddtProvider, MockDhqgDgnlProvider

def submit(api, submission):
    r = api.client.post("/ho-so", json=submission, headers=api.student)
    assert r.status_code == 201, r.text
    return r.json()["ma_ho_so"]

def test_submit_lookup_approve_publish(api, submission):
    key = submit(api, submission)
    year = datetime.now().year
    with api.db.begin() as db:
        db.get(NguyenVongSinhVien, key).nam_tuyen_sinh = year
    assert api.client.patch(f"/ho-so/{key}/duyet", headers=api.student).status_code == 403
    payload = {"nam_tuyen_sinh": year}
    assert api.client.post("/ho-so/cong-bo-ket-qua", json=payload, headers=api.admin).status_code == 400
    assert api.client.patch(f"/ho-so/{key}/duyet", headers=api.admin).json()["trang_thai"] == "hop_le"
    assert api.client.patch(f"/ho-so/{key}/duyet", headers=api.admin).status_code == 409
    first = api.client.post("/ho-so/cong-bo-ket-qua", json=payload, headers=api.admin)
    assert first.status_code == 200, first.text
    assert first.json()["notification_triggered"] is False  # No-op publisher is reported honestly.
    own = api.client.get(f"/ho-so/cua-toi/{key}", headers=api.student).json()
    assert own["ket_qua"]
    second = api.client.post("/ho-so/cong-bo-ket-qua", json=payload, headers=api.admin)
    assert second.status_code == 200
    assert api.client.get(f"/ho-so/cua-toi/{key}", headers=api.student).json()["ket_qua"] == own["ket_qua"]

def test_rejection_persists_reason(api, submission):
    key = submit(api, submission)
    assert api.client.patch(f"/ho-so/{key}/tu-choi", json={"ly_do": "  "}, headers=api.admin).status_code == 400
    r = api.client.patch(f"/ho-so/{key}/tu-choi", json={"ly_do": "  Missing evidence  "}, headers=api.admin)
    assert r.status_code == 200
    assert r.json()["trang_thai"] == "tu_choi"
    with api.db() as db:
        record = db.get(NguyenVongSinhVien, key)
        assert record.ket_qua == "Missing evidence"
        assert record.ma_admin_xu_ly == "A1"

@pytest.mark.parametrize("mode", ["future", "expired", "unrelated", "missing"])
def test_publication_milestone_rejection(api, mode):
    with api.db.begin() as db:
        row = db.get(LoTrinhTuyenSinh, "EVENT")
        now = datetime.now()
        if mode == "future":
            row.thoi_gian_bat_dau = now+timedelta(days=1)
        elif mode == "expired":
            row.thoi_gian_ket_thuc = now-timedelta(hours=1)
        elif mode == "unrelated":
            row.ten_su_kien = "Receive submissions"
        else:
            db.delete(row)
    assert api.client.post("/ho-so/cong-bo-ket-qua", json={"nam_tuyen_sinh": datetime.now().year}, headers=api.admin).status_code == 400

def test_thpt_sync_and_resync_real_db(api):
    payload = {"nam_hoc": 2026}
    assert api.client.post("/diem/dong-bo-thpt", json=payload, headers=api.student).status_code == 403
    for _ in range(2):
        r = api.client.post("/diem/dong-bo-thpt", json=payload, headers=api.admin)
        assert r.status_code == 200, r.text
        assert (r.json()["so_thanh_cong"], r.json()["so_loi"]) == (2, 0)
    with api.db() as db:
        assert db.scalar(select(func.count()).select_from(BangDiem)) == 2
        assert db.scalar(select(func.count()).select_from(DiemChiTiet)) == 4
        assert sorted(db.scalars(select(DiemChiTiet.diem_so)).all()) == [6, 7.5, 8, 8.5]

@pytest.mark.parametrize("score,status", [(100, 200), (99, 400)])
def test_dgnl_submit_verify_local_source(api, score, status):
    data = {"diem": score, "ngay_cap": "2026-01-01T00:00:00", "file_dinh_kem": "evidence.pdf"}
    r = api.client.post("/diem/dgnl", json=data, headers=api.student)
    assert r.status_code == 200, r.text
    key = r.json()["ma_chung_chi"]
    assert api.client.post("/diem/dgnl", json=data, headers=api.student).status_code == 400
    r = api.client.patch(f"/diem/dgnl/{key}/xac-nhan", headers=api.admin)
    assert r.status_code == status, r.text
    with api.db() as db:
        assert db.get(ChungChi, key).trang_thai_duyet.value == ("hop_le" if status == 200 else "cho")

def test_mock_source_candidate_year_and_value():
    provider = MockDhqgDgnlProvider()
    assert provider.diem_khop("000000000001", "100", 2026)
    for cccd, score, year in [("missing", "100", 2026), ("000000000001", "100", 2025),
            ("000000000001", "99", 2026), ("000000000001", "nan", 2026), ("000000000001", "abc", 2026)]:
        assert not provider.diem_khop(cccd, score, year)
    assert MockBoGddtProvider().fetch_thpt_scores(2025) == []


def test_thpt_source_timeout(api, monkeypatch):
    def timeout(*args):
        raise TimeoutError("synthetic timeout")
    monkeypatch.setattr(MockBoGddtProvider, "fetch_thpt_scores", timeout)
    r = api.client.post("/diem/dong-bo-thpt", json={"nam_hoc": 2026}, headers=api.admin)
    assert r.status_code == 200
    assert r.json()["ket_noi_nguon_ok"] is False
    assert r.json()["so_thanh_cong"] == 0
    with api.db() as db:
        assert db.scalar(select(func.count()).select_from(BangDiem)) == 0

def test_thpt_database_failure_isolated_per_candidate(api):
    from sqlalchemy import event
    def fail_first(_mapper, _connection, target):
        if target.cccd == "000000000001":
            raise RuntimeError("synthetic candidate failure")
    event.listen(BangDiem, "before_insert", fail_first)
    try:
        r = api.client.post("/diem/dong-bo-thpt", json={"nam_hoc": 2026}, headers=api.admin)
    finally:
        event.remove(BangDiem, "before_insert", fail_first)
    assert r.status_code == 200, r.text
    assert (r.json()["so_thanh_cong"], r.json()["so_loi"]) == (1, 1)
    with api.db() as db:
        rows = db.scalars(select(BangDiem)).all()
        assert len(rows) == 1 and rows[0].cccd == "000000000002"

def test_dgnl_reject_request_and_reprocessing(api):
    data = {"diem": 100, "ngay_cap": "2026-01-01T00:00:00", "file_dinh_kem": "e.pdf"}
    r = api.client.post("/diem/dgnl", json=data, headers=api.student)
    key = r.json()["ma_chung_chi"]
    assert len(api.client.get("/diem/dgnl/cho-xac-minh", headers=api.admin).json()) == 1
    assert api.client.patch(f"/diem/dgnl/{key}/yeu-cau-bo-sung", headers=api.admin).status_code == 200
    assert api.client.patch(f"/diem/dgnl/{key}/xac-nhan", headers=api.admin).status_code == 409
    assert api.client.get("/diem/dgnl/cho-xac-minh", headers=api.admin).json() == []

@pytest.mark.parametrize("path", ["/ho-so", "/diem/dgnl/cho-xac-minh"])
def test_admin_lists_deny_candidate(api, path):
    assert api.client.get(path, headers=api.student).status_code == 403
    assert api.client.get(path).status_code == 401

@pytest.mark.parametrize("path,data", [
    ("/ho-so/cong-bo-ket-qua", {"nam_tuyen_sinh": 2026}),
    ("/diem/dong-bo-thpt", {"nam_hoc": 2026}),
])
def test_admin_post_denies_anonymous_and_candidate(api, path, data):
    assert api.client.post(path, json=data, headers=api.student).status_code == 403
    assert api.client.post(path, json=data).status_code == 401

def test_dgnl_verification_source_timeout(api, monkeypatch):
    data = {"diem": 100, "ngay_cap": "2026-01-01T00:00:00", "file_dinh_kem": "e.pdf"}
    key = api.client.post("/diem/dgnl", json=data, headers=api.student).json()["ma_chung_chi"]
    def timeout(*args):
        raise TimeoutError("synthetic source timeout")
    monkeypatch.setattr(MockDhqgDgnlProvider, "diem_khop", timeout)
    assert api.client.patch(f"/diem/dgnl/{key}/xac-nhan", headers=api.admin).status_code == 502
    with api.db() as db:
        assert db.get(ChungChi, key).trang_thai_duyet.value == "cho"

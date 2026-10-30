import pytest
from sqlalchemy import text
from src.models.admission import ChuongTrinhDaoTao
from src.models.ho_so import NguyenVongSinhVien
from src.models.trang_thai_ho_so import TrangThaiHoSo


def setup_change(api, submission):
    with api.db.begin() as db:
        db.add(ChuongTrinhDaoTao(ma_chuong_trinh='P2', ma_nganh='N1', ten_chuong_trinh='Other program'))
        db.execute(text('CREATE TABLE ctdt_to_hop (ma_chuong_trinh TEXT, ma_to_hop TEXT, nam INTEGER)'))
        db.execute(text("INSERT INTO ctdt_to_hop VALUES ('P2','A00',2026)"))
    response = api.client.post('/ho-so', headers=api.student, json=submission)
    assert response.status_code == 201
    return response.json()['ma_ho_so']


@pytest.mark.parametrize('approved', [False, True])
def test_change_pending_or_approved_resets_review_and_preserves_rank(api, submission, approved):
    key = setup_change(api, submission)
    if approved:
        assert api.client.patch(f'/ho-so/{key}/duyet', headers=api.admin).status_code == 200
    response = api.client.put(f'/ho-so/cua-toi/{key}/nganh', headers=api.student,
        json={'ma_chuong_trinh_cu': 'P1', 'ma_chuong_trinh': 'P2'})
    assert response.status_code == 200, response.text
    with api.db() as db:
        row = db.get(NguyenVongSinhVien, key)
        assert row.ma_chuong_trinh == 'P2' and row.nguyen_vong == 1
        assert row.trang_thai == TrangThaiHoSo.cho and row.ma_admin_xu_ly is None


@pytest.mark.parametrize('state', [TrangThaiHoSo.dang_xu_ly, TrangThaiHoSo.do, TrangThaiHoSo.truot, TrangThaiHoSo.tu_choi])
def test_processing_and_final_states_cannot_change_or_withdraw(api, submission, state):
    key = setup_change(api, submission)
    with api.db.begin() as db:
        db.get(NguyenVongSinhVien, key).trang_thai = state
    assert api.client.put(f'/ho-so/cua-toi/{key}/nganh', headers=api.student,
        json={'ma_chuong_trinh_cu': 'P1', 'ma_chuong_trinh': 'P2'}).status_code == 409
    assert api.client.delete(f'/ho-so/cua-toi/{key}', headers=api.student).status_code == 409


def test_foreign_owner_and_stale_program_are_rejected(api, submission):
    key = setup_change(api, submission)
    path = f'/ho-so/cua-toi/{key}/nganh'
    body = {'ma_chuong_trinh_cu': 'P1', 'ma_chuong_trinh': 'P2'}
    assert api.client.put(path, headers=api.other, json=body).status_code == 404
    assert api.client.put(path, headers=api.student, json={**body, 'ma_chuong_trinh_cu': 'old'}).status_code == 409


def test_multiple_programs_allowed_but_change_cannot_duplicate(api, submission):
    key = setup_change(api, submission)
    other = api.client.post('/ho-so', headers=api.student,
        json={**submission, 'ma_chuong_trinh': 'P2', 'nguyen_vong': 2})
    assert other.status_code == 201
    assert api.client.put(f'/ho-so/cua-toi/{key}/nganh', headers=api.student,
        json={'ma_chuong_trinh_cu': 'P1', 'ma_chuong_trinh': 'P2'}).status_code == 409

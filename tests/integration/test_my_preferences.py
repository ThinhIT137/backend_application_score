from datetime import datetime
from src.models.ho_so import NguyenVongSinhVien
from src.models.trang_thai_ho_so import TrangThaiHoSo as State


def test_my_preferences_scoped_sorted_and_unpublished_hidden(api, submission):
    first = api.client.post('/ho-so', headers=api.student, json={**submission, 'nguyen_vong':2}).json()['ma_ho_so']
    second = api.client.post('/ho-so', headers=api.student, json={**submission, 'nguyen_vong':1}).json()['ma_ho_so']
    foreign = api.client.post('/ho-so', headers=api.other, json=submission).json()['ma_ho_so']
    with api.db.begin() as db:
        row = db.get(NguyenVongSinhVien,first)
        row.trang_thai = State.do
        row.chot_ket_qua_at = datetime.now()
        row.ket_qua = 'Trúng tuyển chưa công bố'
    assert api.client.get('/ho-so/cua-toi').status_code == 401
    assert api.client.get('/ho-so/cua-toi', headers=api.admin).status_code == 403
    response = api.client.get('/ho-so/cua-toi?cccd=000000000002', headers=api.student)
    assert response.status_code == 200
    rows = response.json()
    assert [r['ma_ho_so'] for r in rows] == [second,first]
    assert foreign not in str(rows)
    assert rows[0]['ten_chuong_trinh'] == 'Ky su CNTT'
    assert rows[1]['trang_thai'] == 'dang_xu_ly' and rows[1]['ket_qua'] is None
    assert all('password' not in r and 'diem_trace' not in r for r in rows)
    with api.db.begin() as db:
        db.get(NguyenVongSinhVien,first).cong_bo_at = datetime.now()
    assert api.client.get('/ho-so/cua-toi', headers=api.student).json()[1]['trang_thai'] == 'do'


def test_my_preferences_empty(api):
    response = api.client.get('/ho-so/cua-toi', headers=api.student)
    assert response.status_code == 200 and response.json() == []

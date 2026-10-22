from datetime import datetime
import pytest
from sqlalchemy import select, func
from src.models.ho_so import NguyenVongSinhVien
from src.models.diem_thi_sinh import BangDiem, ChungChi
from src.models.workflow import NotificationOutbox
from src.models.trang_thai_ho_so import TrangThaiHoSo, NguonDuLieu

KEY = '000000000001/11111111-1111-4111-8111-111111111111.pdf'

def submit(api, payload, rank=1, year=2026, headers=None):
    response = api.client.post('/ho-so', headers=headers or api.student,
        json={**payload, 'nguyen_vong': rank, 'nam_tuyen_sinh': year})
    assert response.status_code == 201, response.text
    return response.json()['ma_ho_so']

def body(ids, ranks=None, year=2026):
    return {'nam_tuyen_sinh': year, 'thu_tu': [
        {'ma_ho_so': key, 'nguyen_vong_cu': rank} for key, rank in zip(ids, ranks or range(1, len(ids)+1))]}

def persisted(api, ids):
    with api.db() as db:
        return {key: (db.get(NguyenVongSinhVien, key).nguyen_vong, db.get(NguyenVongSinhVien, key).nam_tuyen_sinh) for key in ids}

def test_reorder_preserves_rank_gaps_year_and_rejects_stale(api, submission):
    a, b = submit(api, submission, 2), submit(api, submission, 5)
    old = submit(api, submission, 1, 2025)
    response = api.client.put('/ho-so/cua-toi/thu-tu', headers=api.student, json=body([b,a], [5,2]))
    assert response.status_code == 200, response.text
    assert persisted(api, [a,b,old]) == {a:(5,2026), b:(2,2026), old:(1,2025)}
    assert api.client.put('/ho-so/cua-toi/thu-tu', headers=api.student, json=body([b,a], [5,2])).status_code == 409
    assert persisted(api,[a,b]) == {a:(5,2026),b:(2,2026)}

@pytest.mark.parametrize('mode', ['missing','foreign','extra','duplicate','stale','wrong-year'])
def test_invalid_order_never_partially_changes_rows(api, submission, mode):
    a,b = submit(api, submission, 1), submit(api, submission, 2)
    foreign = submit(api, submission, 1, headers=api.other)
    payload = body([b,a], [2,1]); expected = 409
    if mode == 'missing': payload = body([a])
    elif mode == 'foreign': payload = body([foreign,a],[2,1]); expected = 404
    elif mode == 'extra': payload['thu_tu'].append({'ma_ho_so':'unknown','nguyen_vong_cu':3}); expected = 404
    elif mode == 'duplicate': payload = body([a,a]); expected = 422
    elif mode == 'stale': payload = body([b,a],[3,1])
    else: payload['nam_tuyen_sinh'] = 2025; expected = 404
    response=api.client.put('/ho-so/cua-toi/thu-tu', headers=api.student,json=payload)
    assert response.status_code == expected, response.text
    assert persisted(api,[a,b]) == {a:(1,2026),b:(2,2026)}

@pytest.mark.parametrize('field,value', [
    ('trang_thai',TrangThaiHoSo.hop_le), ('nguon_du_lieu',NguonDuLieu.dong_bo_bo),
    ('ma_admin_xu_ly','A1'), ('tong_diem_xet_tuyen',0), ('diem_uu_tien_ap_dung',0),
    ('ket_qua','pending decision'), ('nguon_ket_qua','admin'), ('diem_trace',{}),
    ('chot_ket_qua_at',datetime(2026,1,1)), ('cong_bo_at',datetime(2026,1,1)), ('outbox',None)])
def test_processing_metadata_blocks_both_mutations_and_edit_flag(api, submission, field,value):
    a,b = submit(api,submission,1),submit(api,submission,2)
    with api.db.begin() as db:
        if field == 'outbox': db.add(NotificationOutbox(ma_ho_so=a))
        else: setattr(db.get(NguyenVongSinhVien,a),field,value)
    assert api.client.put('/ho-so/cua-toi/thu-tu', headers=api.student,json=body([b,a],[2,1])).status_code == 409
    assert api.client.delete(f'/ho-so/cua-toi/{a}', headers=api.student).status_code == 409
    assert persisted(api,[a,b]) == {a:(1,2026),b:(2,2026)}
    rows=api.client.get('/ho-so/cua-toi',headers=api.student).json()
    assert next(row for row in rows if row['ma_ho_so']==a)['co_the_chinh_sua'] is False

def test_withdraw_preserves_shared_evidence_and_other_dossiers(api,submission):
    payload={**submission,'chung_chi':[{'loai_chung_chi':'IELTS','diem_hoac_hang':'7','file_dinh_kem':KEY}]}
    a,b=submit(api,payload,1),submit(api,submission,2)
    with api.db() as db:
        counts=[db.scalar(select(func.count()).select_from(model)) for model in [BangDiem,ChungChi]]
    assert counts == [2,1]
    assert api.client.delete(f'/ho-so/cua-toi/{a}',headers=api.student).status_code==200
    with api.db() as db:
        assert db.get(NguyenVongSinhVien,a) is None
        assert db.get(NguyenVongSinhVien,b) is not None
        assert [db.scalar(select(func.count()).select_from(model)) for model in [BangDiem,ChungChi]] == counts
    assert a not in str(api.client.get('/ho-so/cua-toi',headers=api.student).json())
    assert api.client.delete(f'/ho-so/cua-toi/{a}',headers=api.student).status_code==404

def test_mutation_auth_and_owner_obfuscation(api,submission):
    a=submit(api,submission)
    for headers,status in [({},401),(api.admin,403),(api.token(expired=True),401)]:
        assert api.client.put('/ho-so/cua-toi/thu-tu',headers=headers,json=body([a])).status_code==status
        assert api.client.delete(f'/ho-so/cua-toi/{a}',headers=headers).status_code==status
    assert api.client.delete(f'/ho-so/cua-toi/{a}',headers=api.other).status_code==404
    assert api.client.put('/ho-so/cua-toi/thu-tu',headers=api.other,json=body([a])).status_code==404

@pytest.mark.parametrize('key,status',[(KEY,201),(KEY.replace('.pdf','.jpg'),201),(KEY.replace('.pdf','.png'),201),
    ('https://example.test/'+KEY,400),('../'+KEY,400),('000000000002/'+KEY.split('/')[1],403),
    (KEY+'?download=1',400),(KEY+'#x',400),('000000000001/../file.pdf',400),('file.pdf',400),
    (KEY.replace('/','%2f'),400),(KEY.replace('.pdf','.svg'),400)])
def test_evidence_key_exact_storage_format(api,submission,key,status):
    payload={**submission,'chung_chi':[{'loai_chung_chi':'IELTS','diem_hoac_hang':'7','file_dinh_kem':key}]}
    response=api.client.post('/ho-so',headers=api.student,json=payload)
    assert response.status_code==status,response.text
    if status!=201:
        with api.db() as db: assert db.scalar(select(func.count()).select_from(NguyenVongSinhVien))==0

from sqlalchemy import select, func
from jose import jwt
from datetime import datetime, timedelta, timezone
from src.core import security
from src.models.submission_operation import SubmissionOperation
from src.models.diem_thi_sinh import ChungChi
from src.models.ho_so import NguyenVongSinhVien

KEY = '000000000001/11111111-1111-4111-8111-111111111111.png'


def submit(api, submission, rank=1):
    response = api.client.post('/ho-so', headers=api.student, json={**submission,
        'nguyen_vong': rank, 'chung_chi': [{'loai_chung_chi': 'Minh chứng', 'diem_hoac_hang': 'Bản số hóa', 'file_dinh_kem': KEY}]})
    assert response.status_code == 201, response.text
    return response.json()['ma_ho_so']


def test_last_withdrawal_queues_files_and_blocks_reuse_until_server_receipt(api, submission):
    dossier = submit(api, submission)
    path = f'/ho-so/cua-toi/{dossier}'
    response = api.client.delete(path, headers=api.student)
    assert response.status_code == 200, response.text
    job = response.json()
    assert job['files'] == [KEY]
    with api.db() as db:
        assert db.get(NguyenVongSinhVien, dossier) is None
        assert db.scalar(select(func.count()).select_from(ChungChi)) == 0
        assert db.get(SubmissionOperation, job['operation_id']).status == 'withdraw_cleanup'
    # A dropped HTTP/Storage response must not lose the durable cleanup job.
    assert api.client.delete(path, headers=api.student).json() == job
    assert api.client.get('/ho-so/cua-toi/don-minh-chung', headers=api.student).json() == [job]
    assert api.client.get('/ho-so/cua-toi/don-minh-chung', headers=api.other).json() == []
    assert api.client.post('/ho-so', headers=api.student, json=submission).status_code == 409
    complete = '/ho-so/cua-toi/don-minh-chung/' + job['operation_id']
    assert api.client.post(complete, headers=api.student, json={'proof': 'fake'}).status_code == 403
    assert api.client.post(complete, headers=api.student, json={'proof': None}).status_code == 403
    proof = jwt.encode({'sub': '000000000001', 'aud': 'withdraw-cleanup',
        'operation_id': job['operation_id'], 'exp': datetime.now(timezone.utc) + timedelta(minutes=1)},
        security.get_settings().jwt_secret, algorithm='HS256')
    assert api.client.post(complete, headers=api.other, json={'proof': proof}).status_code == 403
    assert api.client.post(complete, headers=api.student, json={'proof': proof}).status_code == 200
    assert api.client.post(complete, headers=api.student, json={'proof': proof}).status_code == 200
    assert api.client.get('/ho-so/cua-toi/don-minh-chung', headers=api.student).json() == []
    assert api.client.post('/ho-so', headers=api.student, json=submission).status_code == 201


def test_shared_images_are_retained_until_last_dossier_across_years(api, submission):
    first = submit(api, submission)
    second = submit(api, {**submission, 'nam_tuyen_sinh': 2025}, rank=2)
    response = api.client.delete(f'/ho-so/cua-toi/{first}', headers=api.student)
    assert response.status_code == 200
    assert 'files' not in response.json()
    with api.db() as db:
        assert db.scalar(select(func.count()).select_from(ChungChi)) == 2
    response = api.client.delete(f'/ho-so/cua-toi/{second}', headers=api.student)
    assert response.status_code == 200
    assert response.json()['files'] == [KEY]

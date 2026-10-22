"""Sprint 3: real HTTP/JWT/repositories, isolated SQLite; no outbound mail."""
from datetime import datetime, timedelta
from unittest.mock import Mock
from tests.integration.test_profile_lifecycle import decide
import pytest
from src.models.ho_so import NguyenVongSinhVien
from src.models.tham_chieu import LoTrinhTuyenSinh
from src.models.trang_thai_ho_so import TrangThaiDuyet
from src.services.notification_service import NotificationService


def approved(api, submission):
    year = datetime.now().year
    response = api.client.post('/ho-so', json={**submission, 'nam_tuyen_sinh': year}, headers=api.student)
    assert response.status_code == 201, response.text
    key = response.json()['ma_ho_so']
    response = api.client.patch(f'/ho-so/{key}/duyet', headers=api.admin)
    assert response.status_code == 200
    return key, year


def test_published_result_lookup_and_filters(api, submission):
    key, year = approved(api, submission)
    decide(api, key, year)
    response = api.client.post('/ho-so/cong-bo-ket-qua', json={'nam_tuyen_sinh': year}, headers=api.admin)
    assert response.status_code == 200, response.text
    response = api.client.get('/ho-so/ket-qua/tra-cuu', headers=api.student, params={'cccd': '000000000001', 'nam_tuyen_sinh': year})
    assert response.status_code == 200
    row = response.json()[0]
    assert row['ma_ho_so'] == key
    assert row['timeline_trang_thai'] == 'trung_tuyen'
    assert 'đã công bố' in row['ket_qua']
    for filters in [{'nguyen_vong': 2}, {'ket_qua': 'khong_trung_tuyen'}]:
        response = api.client.get('/ho-so/ket-qua/tra-cuu', headers=api.student, params={'ma_ho_so': key, 'nam_tuyen_sinh': year, **filters})
        assert response.status_code == 200
        assert response.json() == []
    assert api.client.get('/ho-so/ket-qua', params={'nam_tuyen_sinh': year, 'page_size': 1, 'page': 2}, headers=api.admin).json() == []


@pytest.mark.parametrize('window', ['future', 'expired', 'missing'])
def test_results_hidden_outside_publication_window(api, submission, window):
    key, year = approved(api, submission)
    with api.db.begin() as db:
        event = db.get(LoTrinhTuyenSinh, 'EVENT')
        if window == 'missing':
            db.delete(event)
        elif window == 'future':
            event.thoi_gian_bat_dau = datetime.now() + timedelta(days=2)
        else:
            event.thoi_gian_ket_thuc = datetime.now() - timedelta(days=2)
    response = api.client.get('/ho-so/ket-qua/tra-cuu', headers=api.student, params={'ma_ho_so': key, 'nam_tuyen_sinh': year})
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize('auth,status', [('anonymous', 401), ('student', 403), ('admin', 200)])
def test_result_management_access(api, auth, status):
    headers = {} if auth == 'anonymous' else getattr(api, auth)
    assert api.client.get('/ho-so/ket-qua', headers=headers).status_code == status


@pytest.mark.parametrize('query', ['page=0', 'page_size=101', 'page_size=0'])
def test_results_pagination_validation(api, query):
    assert api.client.get('/ho-so/ket-qua?' + query, headers=api.admin).status_code == 422


def test_notification_continues_after_one_sender_failure(record):
    from copy import copy
    other = copy(record)
    other.ma_ho_so = 'H2'
    other.cccd = '002'
    sender = Mock()
    sender.send.side_effect = [RuntimeError('test SMTP failure'), None]
    service = NotificationService(sender)
    report = service.send_for_records([record, other], get_email_thi_sinh=lambda _: ' test@example.invalid ')
    assert report == {'tong': 2, 'da_gui': 1, 'thieu_email': 0, 'loi': 1, 'ma_ho_so_loi': ['H1']}
    assert sender.send.call_count == 2
    assert sender.send.call_args.args[0] == 'test@example.invalid'
    assert 'H2' in sender.send.call_args.args[1]


def test_notification_empty_batch_and_missing_address(record):
    sender = Mock()
    service = NotificationService(sender)
    assert service.send_for_records([])['tong'] == 0
    assert service.send_for_records([record], get_email_thi_sinh=lambda _: '  ')['thieu_email'] == 1
    sender.send.assert_not_called()

"""Sprint 4: permissions, filtering, empty data, pagination and aggregation."""
import pytest
from tests.integration.test_statistics_reports import _seed_report_data

PATHS = ['/thong-ke/tong-quan', '/thong-ke/nganh-hoc', '/thong-ke/xet-tuyen', '/bao-cao/trung-tuyen']


@pytest.mark.parametrize('path', PATHS)
@pytest.mark.parametrize('role,status', [('anonymous', 401), ('student', 403), ('expired', 401)])
def test_reports_access_control(api, path, role, status):
    headers = {} if role == 'anonymous' else api.token(expired=True) if role == 'expired' else api.student
    assert api.client.get(path, headers=headers).status_code == status


@pytest.mark.parametrize('path', PATHS)
@pytest.mark.parametrize('query', ['nam_tuyen_sinh=1999', 'nam_tuyen_sinh=2101', 'tu_ngay=bad-date'])
def test_report_input_validation(api, path, query):
    assert api.client.get(path + '?' + query, headers=api.admin).status_code == 422


def test_empty_statistics_are_finite_and_no_rows_leak_across_years(api):
    _seed_report_data(api)
    response = api.client.get('/thong-ke/tong-quan?nam_tuyen_sinh=2025', headers=api.admin)
    assert response.status_code == 200
    data = response.json()
    for key in ['tong_ho_so', 'trung_tuyen', 'tong_chi_tieu', 'ty_le_hoan_tat', 'ty_le_trung_tuyen']:
        assert data[key] == 0
    assert data['xu_huong_theo_ngay'] == []


@pytest.mark.parametrize('filters,expected', [
    ({'ma_phuong_thuc': 'CC'}, {'HS3'}), ({'ma_to_hop': 'A00'}, {'HS1', 'HS2'}),
    ({'ma_nganh': 'missing'}, set()), ({'ma_chuong_trinh': 'missing'}, set()),
    ({'ket_qua': 'khong_trung_tuyen'}, {'HS2'}), ({'ket_qua': 'chua_cong_bo'}, {'HS3'}),
    ({'tu_ngay': '2026-06-11', 'den_ngay': '2026-06-11'}, {'HS2', 'HS3'}),
])
def test_report_filters(api, filters, expected):
    _seed_report_data(api)
    response = api.client.get('/bao-cao/trung-tuyen', params={'nam_tuyen_sinh': 2026, **filters}, headers=api.admin)
    assert response.status_code == 200, response.text
    data = response.json()
    assert {r['ma_ho_so'] for r in data['du_lieu']} == expected
    assert data['phan_trang']['total'] == len(expected)
    assert data['tong_hop']['tong_ho_so'] == len(expected)


def test_report_pagination_is_stable_and_non_overlapping(api):
    _seed_report_data(api)
    pages = []
    for page in range(1, 5):
        response = api.client.get('/bao-cao/trung-tuyen', params={'nam_tuyen_sinh': 2026, 'page_size': 1, 'page': page}, headers=api.admin)
        assert response.status_code == 200
        data = response.json()
        assert data['phan_trang']['total'] == 3
        assert data['phan_trang']['total_pages'] == 3
        pages.extend(r['ma_ho_so'] for r in data['du_lieu'])
    assert len(pages) == len(set(pages)) == 3


@pytest.mark.parametrize('query', ['page=0', 'page_size=101', 'ket_qua=invalid'])
def test_report_pagination_and_outcome_validation(api, query):
    assert api.client.get('/bao-cao/trung-tuyen?' + query, headers=api.admin).status_code == 422

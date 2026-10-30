import pytest
from src.models.admission import PhuongThucXetTuyen
from src.models.diem_chuan import LichSuDiemChuan
from datetime import datetime


@pytest.mark.parametrize('group,maximum,score,status', [
    ('THPT',30,30,201),('THPT',30,31,400),('THPT',30,-1,422),
    ('TSA',100,100,201),('TSA',100,101,400),('HSA',150,150,201),('HSA',150,151,400),
])
def test_cutoff_score_uses_persisted_method_range(api, group, maximum, score, status):
    with api.db.begin() as db:
        db.add(PhuongThucXetTuyen(ma_phuong_thuc='custom100',ten_phuong_thuc='Custom',
            nhom_xet_tuyen=group,diem_toi_thieu=0,diem_toi_da=maximum))
    response=api.client.post('/diem-chuan',headers=api.admin,json={
        'ma_chuong_trinh':'P1','nam':2026,'chi_tieu':50,
        'diem_trung_tuyen':[{'ma_phuong_thuc':'custom100','diem':score}]})
    assert response.status_code==status,response.text


def test_uncategorized_method_never_infers_group_from_code(api):
    with api.db.begin() as db:
        db.add(PhuongThucXetTuyen(ma_phuong_thuc='pt100',ten_phuong_thuc='THPT name only'))
    response=api.client.post('/diem-chuan',headers=api.admin,json={
        'ma_chuong_trinh':'P1','nam':2026,'chi_tieu':50,
        'diem_trung_tuyen':[{'ma_phuong_thuc':'pt100','diem':25}]})
    assert response.status_code==400,response.text


def test_read_quota_before_any_scores_are_entered(api):
    with api.db.begin() as db:
        db.add(LichSuDiemChuan(ma_ls_dc='EMPTY',ma_chuong_trinh='P1',nam=2024,
            chi_tieu=50,ma_admin_cap_nhat='A1',create_at=datetime.now()))
    response=api.client.get('/diem-chuan/EMPTY',headers=api.admin)
    assert response.status_code==200,response.text
    assert response.json()['diem_trung_tuyen']==[]

from src.models.diem_chuan import LichSuDiemChuan


def create(api, year=2023):
    payload={'ma_chuong_trinh':'P1','nam':year,'chi_tieu':50,
        'diem_trung_tuyen':[{'ma_phuong_thuc':'HB','diem':25}]}
    response=api.client.post('/diem-chuan',headers=api.admin,json=payload)
    assert response.status_code==201,response.text
    return response.json(),payload


def test_lock_year_requires_admin_and_exact_confirmation(api):
    path='/diem-chuan/nam/2023/khoa'
    assert api.client.post(path,headers=api.student,json={'confirmation_year':2023}).status_code==403
    assert api.client.post(path,headers=api.admin,json={'confirmation_year':2022}).status_code==400
    assert api.client.get(path,headers=api.admin).json()['locked'] is False
    assert api.client.post(path,headers=api.admin,json={'confirmation_year':2023}).status_code==200
    assert api.client.post(path,headers=api.admin,json={'confirmation_year':2023}).status_code==200
    assert api.client.get(path,headers=api.admin).json()['locked'] is True


def test_locked_year_blocks_score_update_create_and_delete_but_keeps_quota_editable(api):
    record,payload=create(api)
    key=record['ma_ls_dc'];score_id=record['diem_trung_tuyen'][0]['ma_diem_tt']
    assert api.client.post('/diem-chuan/nam/2023/khoa',headers=api.admin,json={'confirmation_year':2023}).status_code==200
    bad={**payload,'diem_trung_tuyen':[{'ma_phuong_thuc':'HB','diem':26}]}
    assert api.client.put('/diem-chuan/'+key,headers=api.admin,json=bad).status_code==409
    assert api.client.delete('/diem-chuan/'+key,headers=api.admin).status_code==409
    assert api.client.post('/diem-chuan',headers=api.admin,json=payload).status_code==409
    response=api.client.put('/diem-chuan/'+key,headers=api.admin,json={**payload,'chi_tieu':55})
    assert response.status_code==200,response.text
    assert response.json()['chi_tieu']==55
    assert response.json()['diem_trung_tuyen'][0]['ma_diem_tt']==score_id
    assert response.json()['diem_trung_tuyen'][0]['diem']==25
    # Other years remain editable; locking 2023 has no global side effect.
    other,other_payload=create(api,2024)
    assert api.client.put('/diem-chuan/'+other['ma_ls_dc'],headers=api.admin,
        json={**other_payload,'diem_trung_tuyen':[{'ma_phuong_thuc':'HB','diem':26}]}).status_code==200

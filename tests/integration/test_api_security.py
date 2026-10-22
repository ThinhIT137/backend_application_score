from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
from src.core.api_security import ApiSecurityMiddleware, FixedWindowLimiter
from src.core.config import ApiSecuritySettings
from src.core.exceptions import register_exception_handlers
from src.models.ho_so import NguyenVongSinhVien
from src.models.trang_thai_ho_so import TrangThaiHoSo

@pytest.mark.parametrize('path',['/ho-so/tra-cuu','/ho-so/ket-qua/tra-cuu'])
def test_lookup_real_jwt_ownership_minimal_and_unpublished(api,submission,path):
    key=api.client.post('/ho-so',headers=api.student,json=submission).json()['ma_ho_so']
    with api.db.begin() as db:
        row=db.get(NguyenVongSinhVien,key);row.trang_thai=TrangThaiHoSo.do
        row.ket_qua='PRIVATE DECISION';row.chot_ket_qua_at=datetime.now();row.diem_trace={'internal':'secret'}
    for headers,status in [({},401),(api.admin,403),(api.token(expired=True),401)]:
        response=api.client.get(path,params={'ma_ho_so':key},headers=headers)
        assert response.status_code==status
        assert response.headers['cache-control']=='private, no-store'
        assert response.headers['x-content-type-options']=='nosniff'
    foreign=api.client.get(path,params={'ma_ho_so':key},headers=api.other)
    missing=api.client.get(path,params={'ma_ho_so':'DOES-NOT-EXIST'},headers=api.other)
    assert foreign.status_code==missing.status_code==404
    assert foreign.json()==missing.json()
    assert api.client.get(path,params={'cccd':'000000000001'},headers=api.other).status_code==404
    response=api.client.get(path,params={'ma_ho_so':key},headers=api.student)
    assert response.status_code==200,response.text
    rows=response.json()
    for row in rows:
        assert set(row)<= {'ma_ho_so','ma_chuong_trinh','ma_phuong_thuc','nguyen_vong','nam_tuyen_sinh','trang_thai','ket_qua','create_at','timeline_trang_thai'}
        assert row.get('ket_qua') is None and row['trang_thai'] not in ['do','truot']
    assert 'PRIVATE DECISION' not in response.text and '000000000001' not in response.text and 'secret' not in response.text

def test_limiter_fixed_window_capacity_and_threads():
    now=[0];limiter=FixedWindowLimiter(max_buckets=2,clock=lambda:now[0])
    with ThreadPoolExecutor(max_workers=12) as pool:
        results=list(pool.map(lambda _:limiter.check('same',5,60),range(30)))
    assert results.count(0)==5 and results.count(60)==25
    assert limiter.check('second',1,60)==0
    assert limiter.check('third',1,60)==60
    now[0]=60
    assert limiter.check('third',1,60)==0
    assert len(limiter.buckets)==1

def isolated(settings=None):
    app=FastAPI();register_exception_handlers(app)
    config=settings or ApiSecuritySettings()
    app.add_middleware(CORSMiddleware,allow_origins=config.allowed_origins(),allow_credentials=False,allow_methods=['*'],allow_headers=['*'])
    app.add_middleware(ApiSecurityMiddleware,settings=config)
    calls=[]
    @app.post('/auth/candidate/login')
    async def login(): calls.append('login');return {'ok':True}
    @app.get('/ho-so/tra-cuu')
    async def lookup(): calls.append('lookup');return {'ok':True}
    @app.get('/explode')
    async def explode(): raise RuntimeError('password=SECRET SQL DATABASE_URL')
    return TestClient(app,raise_server_exceptions=False),calls

def test_defaults_rates_body_limits_peer_not_xff_and_private_headers():
    settings=ApiSecuritySettings()
    assert (settings.auth_rate_limit,settings.lookup_rate_limit,settings.auth_max_bytes,settings.json_max_bytes)==(60,120,16384,1048576)
    client,calls=isolated(ApiSecuritySettings(auth_rate_limit=2,lookup_rate_limit=2))
    with client:
        for i in range(2): assert client.post('/auth/candidate/login',headers={'x-forwarded-for':str(i)}).status_code==200
        rejected=client.post('/auth/candidate/login',headers={'x-forwarded-for':'different'})
        assert rejected.status_code==429 and int(rejected.headers['retry-after'])>0
        assert rejected.headers['cache-control']=='private, no-store'
        assert calls==['login','login']
        for i in range(2): assert client.get('/ho-so/tra-cuu',headers={'x-forwarded-for':str(i)}).status_code==200
        assert client.get('/ho-so/tra-cuu').status_code==429

def test_actual_streamed_body_limit_before_handler_even_false_length_and_generic_500():
    client,calls=isolated()
    with client:
        response=client.post('/auth/candidate/login',content=iter([b'x'*9000,b'x'*9000]),headers={'content-length':'1'})
        assert response.status_code==413 and calls==[]
        error=client.get('/explode')
        assert error.status_code==500
        assert 'SECRET' not in error.text and 'DATABASE_URL' not in error.text

def test_cors_explicit_csv_default_none_and_reject_wildcard():
    assert ApiSecuritySettings().allowed_origins()==[]
    with pytest.raises(ValueError): ApiSecuritySettings(cors_origins='*')
    config=ApiSecuritySettings(cors_origins='https://allowed.test, https://second.test')
    client,_=isolated(config)
    with client:
        allowed=client.options('/ho-so/tra-cuu',headers={'origin':'https://allowed.test','access-control-request-method':'GET'})
        assert allowed.headers['access-control-allow-origin']=='https://allowed.test'
        assert 'access-control-allow-credentials' not in allowed.headers
        denied=client.options('/ho-so/tra-cuu',headers={'origin':'https://evil.test','access-control-request-method':'GET'})
        assert denied.status_code==400 and 'access-control-allow-origin' not in denied.headers

def test_validation_does_not_reflect_secret_input(api):
    response=api.client.post('/auth/candidate/login',json={'cccd':{'password':'SECRET-TOKEN-OTP'},'password':['SECRET-TOKEN-OTP']})
    assert response.status_code==422 and 'SECRET-TOKEN-OTP' not in response.text

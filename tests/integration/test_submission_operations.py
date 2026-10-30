import hashlib
import json
import time
from uuid import uuid4
from jose import jwt
from src.models.submission_operation import SubmissionOperation
from src.models.diem_thi_sinh import ChungChi
from src.models.trang_thai_ho_so import TrangThaiDuyet
from src.models.ho_so import NguyenVongSinhVien
from src.models.tham_chieu import ThiSinh

KEY = 'public-test-only-key-32-characters'

def fixture(api, submission, monkeypatch, cert_type='IELTS'):
    import src.router.submission_operation_router as router
    from types import SimpleNamespace
    monkeypatch.setattr(router, 'get_settings', lambda: SimpleNamespace(jwt_secret=KEY))
    oid, run = str(uuid4()), str(uuid4())
    doc = json.dumps({'submission':{**submission,'chung_chi':[{'loai_chung_chi':cert_type,'diem_hoac_hang':'7','file_dinh_kem':'000000000001/11111111-1111-4111-8111-111111111111.png'}]},'profile':{'ho_ten':'New profile','so_dien_thoai':'0900000003','khu_vuc':'KV3','doi_tuong_uu_tien':'none'},'files':[]})
    def proof(target, **changes):
        return jwt.encode({'purpose':'submission-coordinator','operation_id':oid,'action':target,'run_id':run,'sub':'000000000001','aud':'submission-coordinator','exp':time.time()+300,'payload_hash':hashlib.sha256(doc.encode()).hexdigest(),**changes},KEY,algorithm='HS256')
    def command(action):
        return api.client.post(f'/submission-operations/{oid}/{action}',headers=api.student,json={'run_id':run,'proof':proof(action)})
    def create(token=None, document=None):
        actual=doc if document is None else document
        return api.client.post('/submission-operations',headers=api.student,json={'operation_id':oid,'document':actual,'run_id':run,'proof':token or proof('create',payload_hash=hashlib.sha256(actual.encode()).hexdigest())})
    return oid,create,command,proof

def test_operation_commit_then_abort_restores_exact_profile_and_preserves_old_dossier(api,submission,monkeypatch):
    old = api.client.post('/ho-so',headers=api.student,json={**submission,'nguyen_vong':2}).json()['ma_ho_so']
    oid,create,command,_=fixture(api,submission,monkeypatch)
    r=create();assert r.status_code==200,r.text
    dossier=r.json()['ma_ho_so']
    with api.db() as db:
        assert db.get(ThiSinh,'000000000001').ho_ten=='New profile'
        assert db.get(SubmissionOperation,oid).status=='pending'
    assert command('abort').status_code==200
    assert command('compensate').status_code==200
    assert command('compensate').status_code==200
    with api.db() as db:
        assert db.get(SubmissionOperation,oid).status=='cleanup_pending'
    assert command('cleanup-complete').status_code==200
    assert command('cleanup-complete').status_code==200
    with api.db() as db:
        assert db.get(NguyenVongSinhVien,dossier) is None
        assert db.get(NguyenVongSinhVien,old) is not None
        assert db.get(ThiSinh,'000000000001').ho_ten=='Nguyen Van A'

def test_completed_operation_retries_are_idempotent_and_cannot_abort(api,submission,monkeypatch):
    oid,create,command,_=fixture(api,submission,monkeypatch)
    first=create();assert first.status_code==200,first.text
    assert create().status_code==409
    assert command('finalize').status_code==200
    assert command('finalize').status_code==200
    assert create().json()['ma_ho_so']==first.json()['ma_ho_so']
    assert command('abort').status_code==409

def test_coordinator_receipt_requires_purpose_subject_run_hash_and_action(api,submission,monkeypatch):
    _,create,_,proof=fixture(api,submission,monkeypatch)
    for change in ({'purpose':'access'},{'sub':'000000000002'},{'run_id':'other'},{'payload_hash':'other'},{'action':'finalize'},{'exp':time.time()-1}):
        assert create(proof('create',**change)).status_code==403

def test_processed_new_certificate_prevents_rollback(api,submission,monkeypatch):
    oid,create,command,_=fixture(api,submission,monkeypatch)
    assert create().status_code==200
    with api.db.begin() as db:
        op=db.get(SubmissionOperation,oid)
        db.get(ChungChi,op.journal['certificates'][0]).trang_thai_duyet=TrangThaiDuyet.hop_le
    assert command('abort').status_code==409

def test_notification_outbox_prevents_abort_before_deleting_files(api,submission,monkeypatch):
    from src.models.workflow import NotificationOutbox
    oid,create,command,_=fixture(api,submission,monkeypatch)
    assert create().status_code==200
    with api.db.begin() as db:
        op=db.get(SubmissionOperation,oid)
        db.add(NotificationOutbox(ma_ho_so=op.dossier_id,email='fixture@example.invalid'))
    assert command('abort').status_code==409

def test_changed_profile_prevents_abort_before_deleting_files(api,submission,monkeypatch):
    _,create,command,_=fixture(api,submission,monkeypatch)
    assert create().status_code==200
    with api.db.begin() as db:
        db.get(ThiSinh,'000000000001').ho_ten='Changed independently'
    assert command('abort').status_code==409

def test_cleanup_pending_blocks_new_submission_until_storage_ack(api,submission,monkeypatch):
    oid,create,command,_=fixture(api,submission,monkeypatch)
    assert create().status_code==200
    assert command('abort').status_code==200
    assert command('compensate').status_code==200
    with api.db() as db:
        assert db.get(SubmissionOperation,oid).status=='cleanup_pending'
    assert api.client.post('/ho-so',headers=api.student,json=submission).status_code==409
    assert command('cleanup-complete').status_code==200
    assert api.client.post('/ho-so',headers=api.student,json=submission).status_code==201

def test_operation_cannot_create_dgnl_certificate_that_has_separate_verification_workflow(api,submission,monkeypatch):
    from src.services.diem_service import LOAI_CHUNG_CHI_DGNL
    oid,create,_,_=fixture(api,submission,monkeypatch,LOAI_CHUNG_CHI_DGNL)
    assert create().status_code==422
    with api.db() as db:
        assert db.get(SubmissionOperation,oid) is None

def test_operation_owner_and_admin_cannot_read_foreign_journal(api,submission,monkeypatch):
    oid,create,_,_=fixture(api,submission,monkeypatch)
    assert create().status_code==200
    assert api.client.get('/submission-operations/'+oid,headers=api.other).status_code==403
    assert api.client.get('/submission-operations/'+oid,headers=api.admin).status_code==403
    assert api.client.get('/submission-operations/'+oid).status_code==401

def test_mutated_transcript_prevents_abort(api,submission,monkeypatch):
    from sqlalchemy import select
    from src.models.diem_thi_sinh import DiemChiTiet
    oid,create,command,_=fixture(api,submission,monkeypatch)
    assert create().status_code==200
    with api.db.begin() as db:
        op=db.get(SubmissionOperation,oid)
        db.scalar(select(DiemChiTiet).where(DiemChiTiet.ma_bang_diem==op.journal['transcripts'][0])).diem_so=1
    assert command('abort').status_code==409

def test_invalid_embedded_document_returns_validation_response_and_no_journal(api,submission,monkeypatch):
    oid,create,_,_=fixture(api,submission,monkeypatch)
    assert create(document='{}').status_code==422
    with api.db() as db:
        assert db.get(SubmissionOperation,oid) is None


def wire_timeline(api, monkeypatch):
    """Observe actual ASGI send ordering, not TestClient's post-cleanup DB state."""
    from app import app
    from fastapi.testclient import TestClient
    from sqlalchemy import event
    events=[]
    def committed(session):
        events.append('commit')
    def rolled_back(session):
        events.append('rollback')
    event.listen(api.db.class_, 'after_commit', committed)
    event.listen(api.db.class_, 'after_rollback', rolled_back)
    async def traced(scope, receive, send):
        async def traced_send(message):
            if message['type']=='http.response.start':
                events.append(('start',message['status']))
            elif message['type']=='http.response.body':
                events.append('body')
            await send(message)
        await app(scope,receive,traced_send)
    client=TestClient(traced,raise_server_exceptions=False)
    monkeypatch.setattr(api,'client',client)
    return events,client,lambda: (event.remove(api.db.class_,'after_commit',committed),event.remove(api.db.class_,'after_rollback',rolled_back))


def test_actual_wire_success_waits_for_commit_for_create_lease_and_commands(api,submission,monkeypatch):
    oid,create,command,_=fixture(api,submission,monkeypatch)
    events,client,remove=wire_timeline(api,monkeypatch)
    try:
        def check(call):
            events.clear()
            response=call()
            assert response.status_code==200,response.text
            assert 'commit' in events,events
            assert events.index('commit') < events.index(('start',200)),events
        check(create)
        with api.db.begin() as db:
            op=db.get(SubmissionOperation,oid)
            op.journal={**op.journal,'lease_until':0}
        check(create)
        check(lambda:command('abort'))
        check(lambda:command('compensate'))
        check(lambda:command('compensate'))
        check(lambda:command('cleanup-complete'))
        check(lambda:command('cleanup-complete'))
        _,create,command,_=fixture(api,submission,monkeypatch)
        check(create)
        check(lambda:command('finalize'))
        check(lambda:command('finalize'))
        check(create)
    finally:
        client.close();remove()


def test_actual_wire_commit_failure_sends_no_success_and_rolls_back_new_data(api,submission,monkeypatch):
    oid,create,_,_=fixture(api,submission,monkeypatch)
    events,client,remove=wire_timeline(api,monkeypatch)
    try:
        with monkeypatch.context() as patch:
            def failure(session):
                events.append('commit-failed')
                raise RuntimeError('injected commit failure')
            patch.setattr(api.db.class_,'commit',failure)
            response=create()
        assert response.status_code==500,response.text
        assert ('start',200) not in events,events
        assert 'rollback' in events,events
        with api.db() as db:
            assert db.get(SubmissionOperation,oid) is None
            assert db.get(ThiSinh,'000000000001').ho_ten=='Nguyen Van A'
    finally:
        client.close();remove()

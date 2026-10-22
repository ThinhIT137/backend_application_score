from datetime import datetime, timedelta, timezone
from src.models.tham_chieu import ThiSinh
from src.models.diem_thi_sinh import BangDiem
from src.models.giai_thuong import GiaiThuong
import src.router.candidate_auth_router as auth


def prepare(api):
    with api.db.begin() as db:
        db.get(ThiSinh, "000000000001").email = "stored@example.invalid"


def test_activation_destination_cooldown_one_use_and_preserves_identity(api, monkeypatch):
    prepare(api)
    messages = []
    monkeypatch.setattr(auth, "send_activation", lambda channel, destination, code: messages.append((channel, destination, code)))
    request = {"cccd": "000000000001", "channel": "email"}
    assert api.client.post("/auth/candidate/activation/request", json=request).status_code == 200
    assert messages[0][1] == "stored@example.invalid"
    assert api.client.post("/auth/candidate/activation/request", json=request).status_code == 200
    assert len(messages) == 1
    confirm = {"cccd": request["cccd"], "password": "VerifiedPassword123!", "otp": messages[0][2]}
    response = api.client.post("/auth/candidate/activation/confirm", json=confirm)
    assert response.status_code == 200
    assert "access_token" in response.json() and "otp" not in response.json()
    assert api.client.post("/auth/candidate/activation/confirm", json=confirm).status_code == 401
    with api.db() as db:
        row = db.get(ThiSinh, request["cccd"])
        assert row.ho_ten == "Nguyen Van A" and row.activation_otp_hash is None
        assert row.password != confirm["password"]


def test_activation_attempt_limit_expiry_and_no_contact_override(api, monkeypatch):
    prepare(api)
    messages = []
    monkeypatch.setattr(auth, "send_activation", lambda channel, destination, code: messages.append(code))
    body = {"cccd":"000000000001", "channel":"email", "email":"attacker@example.invalid"}
    assert api.client.post("/auth/candidate/activation/request", json=body).status_code == 200
    code = messages[0]
    wrong = "999999" if code != "999999" else "000000"
    for _ in range(5):
        assert api.client.post("/auth/candidate/activation/confirm", json={"cccd":body["cccd"],"password":"VerifiedPassword123!","otp":wrong}).status_code == 401
    assert api.client.post("/auth/candidate/activation/confirm", json={"cccd":body["cccd"],"password":"VerifiedPassword123!","otp":code}).status_code == 401
    with api.db.begin() as db:
        row=db.get(ThiSinh, body["cccd"])
        assert row.activation_otp_attempts == 5
        row.activation_otp_attempts=0
        row.activation_otp_expires=datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(minutes=1)
    assert api.client.post("/auth/candidate/activation/confirm", json={"cccd":body["cccd"],"password":"VerifiedPassword123!","otp":code}).status_code == 401


def test_semesters_award_evidence_persist_and_duplicate_rejected(api, submission):
    transcript=submission["bang_diem"][0]
    payload={**submission,"bang_diem":[{**transcript,"hoc_ky":1},{**transcript,"hoc_ky":2}],
        "giai_thuong":[{"giai_thuong":"giai_nhat","loai_giai_thuong":"tinh","mon_hoc":"toan","file_dinh_kem":"000000000001/33333333-3333-4333-8333-333333333333.png"}]}
    response=api.client.post("/ho-so",headers=api.student,json=payload)
    assert response.status_code == 201, response.text
    with api.db() as db:
        assert sorted(b.hoc_ky for b in db.query(BangDiem).all()) == [1,2]
        assert db.query(GiaiThuong).one().file_dinh_kem == "000000000001/33333333-3333-4333-8333-333333333333.png"
    payload["nguyen_vong"]=2
    payload["bang_diem"]=[{**transcript,"hoc_ky":1},{**transcript,"hoc_ky":1}]
    assert api.client.post("/ho-so",headers=api.student,json=payload).status_code == 422
    payload["bang_diem"]=[]
    payload["giai_thuong"][0]["file_dinh_kem"]="000000000002/33333333-3333-4333-8333-333333333333.png"
    assert api.client.post("/ho-so",headers=api.student,json=payload).status_code == 403

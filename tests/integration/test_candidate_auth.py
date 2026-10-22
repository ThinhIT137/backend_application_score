def account():
    return {"cccd": "000000000099", "password": "CandidateTest!2026", "ho_ten": "Candidate Test", "so_dien_thoai": "0900000099"}


def test_candidate_register_login_stateless_refresh_and_logout(api):
    response = api.client.post("/auth/candidate/register", json=account())
    assert response.status_code == 201
    tokens = response.json()
    from src.models.tham_chieu import ThiSinh
    with api.db() as db:
        candidate = db.get(ThiSinh, account()["cccd"])
        assert candidate.password and candidate.password != account()["password"]
        assert "$" in candidate.password
    headers = {"Authorization": "Bearer " + tokens["access_token"]}
    profile = api.client.get("/auth/candidate/me", headers=headers).json()
    assert "password" not in profile and "refresh_hash" not in profile
    assert api.client.get("/auth/candidate/me", headers=headers).json()["cccd"] == account()["cccd"]
    assert api.client.get("/ho-so", headers=headers).status_code == 403
    assert api.client.patch("/auth/candidate/me", headers=headers, json={"ho_ten": "Updated Candidate", "so_dien_thoai": "0900000099", "khu_vuc": "KV2", "doi_tuong_uu_tien": "NONE"}).status_code == 200
    assert api.client.get("/auth/candidate/me", headers=headers).json()["ho_ten"] == "Updated Candidate"
    assert api.client.post("/ho-so", headers=headers, json={"ma_chuong_trinh": "P1", "ma_phuong_thuc": "HB", "nguyen_vong": 1, "nam_tuyen_sinh": 2026,
        "chung_chi": [{"loai_chung_chi": "IELTS", "diem_hoac_hang": "6.5", "file_dinh_kem": "000000000001/44444444-4444-4444-8444-444444444444.pdf"}]}).status_code == 403
    refreshed = api.client.post("/auth/candidate/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    # Stateless refresh remains usable until expiry; logout only removes browser cookies.
    assert api.client.post("/auth/candidate/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 200
    refresh_as_access = {"Authorization": "Bearer " + refreshed.json()["refresh_token"]}
    assert api.client.get("/auth/candidate/me", headers=refresh_as_access).status_code == 401
    logged_in = api.client.post("/auth/candidate/login", json=account())
    assert logged_in.status_code == 200
    assert api.client.post("/auth/candidate/logout", headers={"Authorization": "Bearer " + logged_in.json()["access_token"]}).status_code == 200
    assert api.client.post("/auth/candidate/refresh", json={"refresh_token": logged_in.json()["refresh_token"]}).status_code == 200
    assert api.client.post("/auth/candidate/login", json={**account(), "password": "WrongPassword123"}).status_code == 401


def test_candidate_registration_cannot_claim_existing_record(api):
    response = api.client.post("/auth/candidate/register", json={**account(), "cccd": "000000000001"})
    assert response.status_code == 400
    assert "access_token" not in response.json()
    assert api.client.post("/auth/candidate/login", json={**account(), "cccd": "000000000001"}).status_code == 401


def test_candidate_auth_rejects_invalid_identity_or_password(api):
    for values in [{"cccd": "12"}, {"password": "short"}, {"so_dien_thoai": "abc"}]:
        assert api.client.post("/auth/candidate/register", json={**account(), **values}).status_code == 422
    assert api.client.post("/auth/candidate/refresh", json={"refresh_token": "invalid"}).status_code == 401

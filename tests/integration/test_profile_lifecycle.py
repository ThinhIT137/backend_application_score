from datetime import datetime
import pytest
from src.models.diem_chuan import LichSuDiemChuan


def decide(api, key, year, result="trung_tuyen"):
    with api.db.begin() as db:
        if not db.get(LichSuDiemChuan, "LIFECYCLE-QUOTA"):
            db.add(LichSuDiemChuan(ma_ls_dc="LIFECYCLE-QUOTA", ma_chuong_trinh="P1", nam=year,
                chi_tieu=2, trung_tuyen=0, ma_admin_cap_nhat="A1", create_at=datetime.now()))
    assert api.client.patch(f"/xet-tuyen/{key}/bat-dau-xu-ly", headers=api.admin).status_code == 200
    response = api.client.post(f"/xet-tuyen/{key}/chot-diem", headers=api.admin,
        json={"kind": "manual", "manual_score": 27.5, "source": "Danh sách điểm đã đối soát TEST"})
    assert response.status_code == 200, response.text
    response = api.client.post("/xet-tuyen/chot-ket-qua", headers=api.admin,
        json={"source": "Quyết định xét tuyển TEST", "rows": [{"ma_ho_so": key, "result": result}]})
    assert response.status_code == 200, response.text


@pytest.mark.parametrize("result,status", [("trung_tuyen", "do"), ("khong_trung_tuyen", "truot")])
def test_single_lifecycle_publication_and_guards(api, submission, result, status):
    key = api.client.post("/ho-so", headers=api.student, json=submission).json()["ma_ho_so"]
    start = f"/xet-tuyen/{key}/bat-dau-xu-ly"
    assert api.client.patch(start, headers=api.student).status_code == 403
    assert api.client.patch(start, headers=api.admin).status_code == 409
    assert api.client.patch(f"/ho-so/{key}/duyet", headers=api.admin).json()["trang_thai"] == "hop_le"
    assert api.client.post("/ho-so/cong-bo-ket-qua", headers=api.admin, json={"nam_tuyen_sinh": 2026}).status_code == 400
    decide(api, key, 2026, result)
    assert api.client.get(f"/ho-so/{key}", headers=api.admin).json()["trang_thai"] == status
    assert api.client.get("/ho-so/tra-cuu", headers=api.student, params={"ma_ho_so": key}).json()[0]["trang_thai"] == "dang_xu_ly"
    own = api.client.get(f"/ho-so/cua-toi/{key}", headers=api.student).json()
    assert own["trang_thai"] == "dang_xu_ly" and own["nguon_ket_qua"] is None
    assert api.client.patch(start, headers=api.admin).status_code == 409
    response = api.client.post("/ho-so/cong-bo-ket-qua", headers=api.admin, json={"nam_tuyen_sinh": 2026})
    assert response.status_code == 200, response.text
    assert api.client.get("/ho-so/tra-cuu", headers=api.student, params={"ma_ho_so": key}).json()[0]["trang_thai"] == status
    assert api.client.post("/ho-so/cong-bo-ket-qua", headers=api.admin, json={"nam_tuyen_sinh": 2026}).json()["idempotent"]
    assert api.client.post(f"/xet-tuyen/{key}/chot-diem", headers=api.admin,
        json={"kind": "manual", "manual_score": 20, "source": "Không được sửa"}).status_code == 409


def test_rejected_is_terminal_and_different_from_failed_admission(api, submission):
    key = api.client.post("/ho-so", headers=api.student, json=submission).json()["ma_ho_so"]
    assert api.client.patch(f"/ho-so/{key}/tu-choi", headers=api.admin, json={"ly_do":"Thiếu hồ sơ"}).status_code == 200
    assert api.client.patch(f"/xet-tuyen/{key}/bat-dau-xu-ly", headers=api.admin).status_code == 409
    assert api.client.post("/xet-tuyen/chot-ket-qua", headers=api.admin,
        json={"source":"Không được bỏ qua kiểm tra", "rows":[{"ma_ho_so":key,"result":"khong_trung_tuyen"}]}).status_code == 400

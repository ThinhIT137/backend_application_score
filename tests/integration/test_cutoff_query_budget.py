"""Response serialization must not issue a query for each cutoff/method."""
from datetime import datetime

import pytest
from sqlalchemy import event

from src.models.admission import ChuongTrinhDaoTao
from src.models.diem_chuan import LichSuDiemChuan, DiemTrungTuyen
from src.schemas.admission_schema import CutoffOutput
from src.services.admission_service import AdmissionService


@pytest.mark.parametrize("size", [1, 40])
def test_full_cutoff_serialization_has_constant_select_budget(api, size):
    now = datetime.now()
    with api.db.begin() as db:
        for index in range(size):
            program = f"BUDGET-P{index}"
            db.add(ChuongTrinhDaoTao(ma_chuong_trinh=program, ma_nganh="N1", ten_chuong_trinh=program))
            db.flush()
            db.add(LichSuDiemChuan(
                ma_ls_dc=f"BUDGET-L{index}", ma_chuong_trinh=program, nam=2026,
                chi_tieu=10, trung_tuyen=0, ma_admin_cap_nhat="A1", create_at=now,
                diem_trung_tuyen=[DiemTrungTuyen(
                    ma_diem_tt=f"BUDGET-D{index}-{method}", ma_phuong_thuc=method,
                    diem=24, create_at=now, dieu_kien_mon={"TOAN": 8},
                ) for method in ("HB", "CC")],
            ))
    with api.db() as db:
        engine = db.get_bind()
    queries = []

    def record(_conn, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith("SELECT"):
            queries.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        with api.db() as db:
            rows = AdmissionService(db).list_cutoffs(2026)
            output = [CutoffOutput.model_validate(row).model_dump() for row in rows]
        assert len(output) == size
        assert len(queries) <= 3, f"{size} cutoffs caused {len(queries)} SELECTs during list + serialization"
        for row in output:
            assert row["chuong_trinh"]["ten_chuong_trinh"].startswith("BUDGET-P")
            assert len(row["diem_trung_tuyen"]) == 2
            assert all(child["phuong_thuc"]["ten_phuong_thuc"] for child in row["diem_trung_tuyen"])
            assert all(child["dieu_kien_mon"] == {"TOAN": 8} for child in row["diem_trung_tuyen"])
        # Even detached ORM rows must contain everything required by the response.
        assert [CutoffOutput.model_validate(row).model_dump() for row in rows] == output
        queries.clear()
        with api.db() as db:
            one = AdmissionService(db).get_cutoff("BUDGET-L0")
            detail = CutoffOutput.model_validate(one).model_dump()
        assert len(queries) <= 3
        assert CutoffOutput.model_validate(one).model_dump() == detail
    finally:
        event.remove(engine, "before_cursor_execute", record)


def test_cutoff_update_response_reloads_changed_program_and_new_child_ids(api):
    with api.db.begin() as db:
        db.add(ChuongTrinhDaoTao(ma_chuong_trinh="P2", ma_nganh="N1", ten_chuong_trinh="Second program"))
    data = {"ma_chuong_trinh": "P1", "nam": 2026, "chi_tieu": 2,
            "diem_trung_tuyen": [{"ma_phuong_thuc": "HB", "diem": 25, "dieu_kien_mon": {"TOAN": 8}}]}
    created = api.client.post("/diem-chuan", json=data, headers=api.admin)
    assert created.status_code == 201
    previous = created.json()
    response = api.client.put(f"/diem-chuan/{previous['ma_ls_dc']}", json={
        **data, "ma_chuong_trinh": "P2", "diem_trung_tuyen": [{"ma_phuong_thuc": "HB", "diem": 0}],
    }, headers=api.admin)
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["chuong_trinh"]["ten_chuong_trinh"] == "Second program"
    assert updated["diem_trung_tuyen"][0]["ma_diem_tt"] != previous["diem_trung_tuyen"][0]["ma_diem_tt"]
    assert updated["diem_trung_tuyen"][0]["diem"] == 0
    assert updated["diem_trung_tuyen"][0]["dieu_kien_mon"] == {"TOAN": 8}
    assert updated["diem_trung_tuyen"][0]["phuong_thuc"]["ten_phuong_thuc"] == "Hoc ba"

from datetime import datetime, timedelta

from src.models.diem_chuan import DiemTrungTuyen, LichSuDiemChuan
from src.models.ho_so import NguyenVongSinhVien
from src.models.trang_thai_ho_so import NguonDuLieu, TrangThaiHoSo as TrangThaiDuyet


def _seed_report_data(api):
    now = datetime(2026, 6, 10, 8, 30)
    with api.db.begin() as db:
        history = LichSuDiemChuan(
            ma_ls_dc="LS1",
            ma_chuong_trinh="P1",
            nam=2026,
            chi_tieu=2,
            trung_tuyen=1,
            ma_admin_cap_nhat="A1",
            create_at=now,
        )
        history.diem_trung_tuyen.append(
            DiemTrungTuyen(
                ma_diem_tt="D1",
                ma_phuong_thuc="HB",
                diem=25.0,
                create_at=now,
            )
        )
        db.add(history)
        db.add_all(
            [
                NguyenVongSinhVien(
                    ma_ho_so="HS1",
                    cccd="000000000001",
                    ma_chuong_trinh="P1",
                    ma_phuong_thuc="HB",
                    ma_to_hop="A00",
                    trang_thai=TrangThaiDuyet.do, cong_bo_at=now, chot_ket_qua_at=now,
                    ket_qua="Đủ điều kiện xét tuyển (đã công bố)",
                    tong_diem_xet_tuyen=27.5,
                    nguon_du_lieu=NguonDuLieu.tu_nop,
                    nguyen_vong=1,
                    nam_tuyen_sinh=2026,
                    create_at=now,
                ),
                NguyenVongSinhVien(
                    ma_ho_so="HS2",
                    cccd="000000000002",
                    ma_chuong_trinh="P1",
                    ma_phuong_thuc="HB",
                    ma_to_hop="A00",
                    trang_thai=TrangThaiDuyet.truot, cong_bo_at=now, chot_ket_qua_at=now,
                    ket_qua="Không đủ điều kiện (đã công bố)",
                    tong_diem_xet_tuyen=20.0,
                    nguon_du_lieu=NguonDuLieu.tu_nop,
                    nguyen_vong=2,
                    nam_tuyen_sinh=2026,
                    create_at=now + timedelta(days=1),
                ),
                NguyenVongSinhVien(
                    ma_ho_so="HS3",
                    cccd="000000000001",
                    ma_chuong_trinh="P1",
                    ma_phuong_thuc="CC",
                    trang_thai=TrangThaiDuyet.cho,
                    ket_qua=None,
                    nguon_du_lieu=NguonDuLieu.tu_nop,
                    nguyen_vong=3,
                    nam_tuyen_sinh=2026,
                    create_at=now + timedelta(days=1),
                ),
            ]
        )


def test_statistics_require_admin(api):
    response = api.client.get("/thong-ke/tong-quan?nam_tuyen_sinh=2026")
    assert response.status_code == 401


def test_overview_and_industry_statistics(api):
    _seed_report_data(api)
    overview = api.client.get(
        "/thong-ke/tong-quan?nam_tuyen_sinh=2026", headers=api.admin
    )
    assert overview.status_code == 200
    assert overview.json() == {
        "nam_tuyen_sinh": 2026,
        "tong_ho_so": 3,
        "cho_xu_ly": 1,
        "hop_le": 2,
        "tu_choi": 0,
        "da_cong_bo": 2,
        "trung_tuyen": 1,
        "tong_chi_tieu": 2,
        "tong_nganh": 1,
        "ty_le_hoan_tat": 66.67,
        "ty_le_trung_tuyen": 33.33,
        "xu_huong_theo_ngay": [
            {"ngay": "2026-06-10", "so_luong": 1},
            {"ngay": "2026-06-11", "so_luong": 2},
        ],
    }

    industry = api.client.get(
        "/thong-ke/nganh-hoc?nam_tuyen_sinh=2026", headers=api.admin
    )
    assert industry.status_code == 200
    assert industry.json()[0] == {
        "ma_nganh": "N1",
        "ten_nganh": "Cong nghe thong tin",
        "chi_tieu": 2,
        "tong_ho_so": 3,
        "hop_le": 2,
        "tu_choi": 0,
        "trung_tuyen": 1,
        "ty_le_canh_tranh": 1.5,
        "ty_le_lap_day": 50.0,
    }


def test_method_combination_and_report_filters(api):
    _seed_report_data(api)
    grouped = api.client.get(
        "/thong-ke/xet-tuyen?nam_tuyen_sinh=2026", headers=api.admin
    )
    assert grouped.status_code == 200
    payload = grouped.json()
    hoc_ba = next(
        item for item in payload["theo_phuong_thuc"] if item["ma_phuong_thuc"] == "HB"
    )
    assert hoc_ba["tong_ho_so"] == 2
    assert hoc_ba["trung_tuyen"] == 1
    assert hoc_ba["ty_trong"] == 66.67
    assert payload["theo_to_hop"][0]["ma_to_hop"] == "A00"
    assert payload["theo_to_hop"][0]["tong_ho_so"] == 2

    report = api.client.get(
        "/bao-cao/trung-tuyen?nam_tuyen_sinh=2026&ket_qua=trung_tuyen&page=1&page_size=10",
        headers=api.admin,
    )
    assert report.status_code == 200
    body = report.json()
    assert body["tong_hop"] == {
        "tong_ho_so": 1,
        "trung_tuyen": 1,
        "khong_trung_tuyen": 0,
        "chua_cong_bo": 0,
    }
    assert body["phan_trang"] == {
        "page": 1,
        "page_size": 10,
        "total": 1,
        "total_pages": 1,
    }
    assert body["du_lieu"][0]["ma_ho_so"] == "HS1"
    assert body["du_lieu"][0]["ho_ten"] == "Nguyen Van A"
    assert body["du_lieu"][0]["diem_chuan"] == 25.0


def test_invalid_date_range_is_rejected(api):
    response = api.client.get(
        "/thong-ke/tong-quan?nam_tuyen_sinh=2026&tu_ngay=2026-06-12&den_ngay=2026-06-01",
        headers=api.admin,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "DU_LIEU_KHONG_HOP_LE"


def test_rejection_reason_is_not_counted_as_published_result(api):
    _seed_report_data(api)
    with api.db.begin() as db:
        rejected = db.get(NguyenVongSinhVien, "HS2")
        rejected.ket_qua = "Thiếu minh chứng"
        rejected.trang_thai = TrangThaiDuyet.tu_choi
        rejected.cong_bo_at = None
        rejected.chot_ket_qua_at = None

    overview = api.client.get(
        "/thong-ke/tong-quan?nam_tuyen_sinh=2026", headers=api.admin
    )
    assert overview.status_code == 200
    assert overview.json()["da_cong_bo"] == 1

    report = api.client.get(
        "/bao-cao/trung-tuyen?nam_tuyen_sinh=2026&ket_qua=chua_cong_bo&page_size=10",
        headers=api.admin,
    )
    assert report.status_code == 200
    assert {item["ma_ho_so"] for item in report.json()["du_lieu"]} == {"HS2", "HS3"}

from datetime import datetime

from src.models.ho_so import NguyenVongSinhVien
from src.models.trang_thai_ho_so import NguonDuLieu, TrangThaiDuyet
from src.services.adapters.email_sender import MockEmailSender
from src.services.notification_service import NotificationService


def _record(ma_ho_so: str, cccd: str, ket_qua: str | None = None) -> NguyenVongSinhVien:
    return NguyenVongSinhVien(
        ma_ho_so=ma_ho_so,
        cccd=cccd,
        ma_chuong_trinh="CNTT",
        trang_thai=TrangThaiDuyet.hop_le,
        ket_qua=ket_qua,
        diem_uu_tien_ap_dung=None,
        tong_diem_xet_tuyen=27.5,
        ma_to_hop=None,
        ma_phuong_thuc="PT100",
        nguon_du_lieu=NguonDuLieu.tu_nop,
        nguyen_vong=1,
        nam_tuyen_sinh=2025,
        ma_admin_xu_ly=None,
        create_at=datetime.now(),
    )


def test_mock_email_sender_collects_sent_messages():
    sender = MockEmailSender()
    sender.send("a@example.com", "Test", "body")

    assert sender.sent_messages[0]["to"] == "a@example.com"
    assert sender.sent_messages[0]["subject"] == "Test"


def test_notification_service_skips_missing_email_and_counts_report():
    sender = MockEmailSender()
    service = NotificationService(sender)

    records = [
        _record("HS-001", "123456789012", "Đủ điều kiện xét tuyển (đã công bố)"),
        _record("HS-002", "123456789013", "Không đủ điều kiện (đã công bố)"),
    ]

    report = service.send_for_records(
        records,
        get_email_thi_sinh=lambda cccd: None if cccd == "123456789013" else "candidate@example.com",
    )

    assert report["tong"] == 2
    assert report["da_gui"] == 1
    assert report["thieu_email"] == 1
    assert report["loi"] == 0
    assert len(sender.sent_messages) == 1

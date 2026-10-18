from datetime import datetime
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from pydantic import ValidationError

from src.models.ho_so import NguyenVongSinhVien
from src.models.trang_thai_ho_so import NguonDuLieu, TrangThaiDuyet
from src.schemas.ho_so_schema import CongBoKetQuaRequest
from src.services.adapters.email_sender import EmailSender, MockEmailSender, SmtpEmailSender
from src.services.adapters.notification import EmailNotificationPublisher, build_notification_publisher
from src.services.ho_so_service import HoSoService
from src.services.notification_service import NotificationService
from src.core.config import Settings
from src.core.exceptions import KhongDuDieuKienCongBo


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


def test_smtp_sender_uses_starttls_and_sends_message(monkeypatch):
    sent_messages = []
    calls = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls.append(("connect", host, port, timeout))

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def starttls(self):
            calls.append(("starttls",))

        def login(self, username, password):
            calls.append(("login", username, password))

        def send_message(self, message):
            sent_messages.append(message)

    monkeypatch.setattr("src.services.adapters.email_sender.smtplib.SMTP", FakeSMTP)
    sender = SmtpEmailSender(
        host="smtp.example.com",
        port=587,
        username="user@example.com",
        password="test-password",
        from_addr="admissions@example.com",
    )

    sender.send("candidate@example.com", "Admission result", "Published")

    assert calls == [
        ("connect", "smtp.example.com", 587, 15.0),
        ("starttls",),
        ("login", "user@example.com", "test-password"),
    ]
    assert sent_messages[0]["To"] == "candidate@example.com"


def test_notification_factory_selects_smtp_when_configured():
    settings = Settings(
        _env_file=None,
        database_url="sqlite://",
        jwt_secret="test-secret-that-is-long-enough",
        email_provider="smtp",
        smtp_host="smtp.example.com",
        smtp_username="user@example.com",
        smtp_password="smtp-test-password",
        smtp_from="admissions@example.com",
    )

    publisher = build_notification_publisher(settings, lambda _cccd: None)

    assert isinstance(publisher, EmailNotificationPublisher)
    assert isinstance(publisher.service.sender, SmtpEmailSender)


def test_smtp_configuration_fails_fast_when_required_settings_are_missing():
    with pytest.raises(ValidationError, match="SMTP_HOST is required"):
        Settings(
            _env_file=None,
            database_url="sqlite://",
            jwt_secret="test-secret-that-is-long-enough",
            email_provider="smtp",
        )


def test_cors_configuration_rejects_wildcard_origins():
    with pytest.raises(ValidationError, match="explicit origins"):
        Settings(
            _env_file=None,
            database_url="sqlite://",
            jwt_secret="test-secret-that-is-long-enough",
            cors_allowed_origins=["*"],
        )


def test_notification_service_continues_after_email_lookup_failure():
    sender = MockEmailSender()
    service = NotificationService(sender)

    def resolve_email(cccd):
        if cccd == "123456789012":
            raise RuntimeError("directory unavailable")
        return "second@example.com"

    report = service.send_for_records(
        [
            _record("HS-004", "123456789012"),
            _record("HS-005", "123456789013"),
        ],
        get_email_thi_sinh=resolve_email,
    )

    assert report["da_gui"] == 1
    assert report["loi"] == 1
    assert report["ma_ho_so_loi"] == ["HS-004"]
    assert len(sender.sent_messages) == 1


def test_publication_commits_before_send_and_does_not_send_twice():
    repository = MagicMock()
    score_repository = MagicMock()
    now = datetime.now()
    score_repository.list_lo_trinh.return_value = [
        SimpleNamespace(
            loai_moc="cong_bo",
            ten_moc="",
            thoi_gian_bat_dau=now - timedelta(days=1),
            thoi_gian_ket_thuc=now + timedelta(days=1),
        )
    ]
    repository.count_cho.return_value = 0
    record = _record("HS-006", "123456789012")
    repository.list_for_cong_bo.return_value = [record]

    class CommitCheckingSender(EmailSender):
        def __init__(self):
            self.sent = 0

        def send(self, to, subject, body):
            assert repository.commit.called
            self.sent += 1

    sender = CommitCheckingSender()
    notifier = EmailNotificationPublisher(sender, lambda _cccd: "candidate@example.com")
    service = HoSoService(repository, score_repository, notifier)
    request = CongBoKetQuaRequest(nam_tuyen_sinh=2025)

    with pytest.raises(KhongDuDieuKienCongBo, match="nguồn kết quả"):
        service.cong_bo_ket_qua(request)

    assert record.ket_qua is None
    assert sender.sent == 0
    repository.commit.assert_not_called()

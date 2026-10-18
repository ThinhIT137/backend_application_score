from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from src.core.config import Settings, get_settings
from src.models.ho_so import NguyenVongSinhVien
from src.services.adapters.email_sender import EmailSender, MockEmailSender, SmtpEmailSender
from src.services.notification_service import NotificationService


class NotificationPublisher(ABC):
    @abstractmethod
    def trigger_cong_bo_ket_qua(
        self,
        nam_tuyen_sinh: int,
        records: list[NguyenVongSinhVien] | None = None,
    ) -> dict[str, Any] | None:
        raise NotImplementedError


class NoOpNotificationPublisher(NotificationPublisher):
    def trigger_cong_bo_ket_qua(
        self,
        nam_tuyen_sinh: int,
        records: list[NguyenVongSinhVien] | None = None,
    ) -> dict[str, Any]:
        _ = nam_tuyen_sinh, records
        return {"tong": 0, "da_gui": 0, "thieu_email": 0, "loi": 0, "ma_ho_so_loi": []}


class EmailNotificationPublisher(NotificationPublisher):
    def __init__(
        self,
        sender: EmailSender | None = None,
        get_email_thi_sinh: Callable[[str], str | None] | None = None,
    ) -> None:
        self.service = NotificationService(sender or MockEmailSender(), get_email_thi_sinh)

    def trigger_cong_bo_ket_qua(
        self,
        nam_tuyen_sinh: int,
        records: list[NguyenVongSinhVien] | None = None,
    ) -> dict[str, Any]:
        _ = nam_tuyen_sinh
        if not records:
            return {"tong": 0, "da_gui": 0, "thieu_email": 0, "loi": 0, "ma_ho_so_loi": []}
        return self.service.send_for_records(records)


def build_notification_publisher(
    settings: Settings | None = None,
    get_email_thi_sinh: Callable[[str], str | None] | None = None,
) -> NotificationPublisher:
    settings = settings or get_settings()
    if settings.email_provider == "smtp":
        sender = SmtpEmailSender(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            use_tls=settings.smtp_use_tls,
            from_addr=settings.smtp_from,
        )
        return EmailNotificationPublisher(sender, get_email_thi_sinh)
    return EmailNotificationPublisher(MockEmailSender(), get_email_thi_sinh)

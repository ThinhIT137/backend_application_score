from __future__ import annotations

import smtplib
from abc import ABC, abstractmethod
from email.message import EmailMessage


class EmailSender(ABC):
    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> None:
        raise NotImplementedError


class MockEmailSender(EmailSender):
    def __init__(self) -> None:
        self.sent_messages: list[dict[str, str]] = []

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent_messages.append({
            "to": to,
            "subject": subject,
            "body": body,
        })


class SmtpEmailSender(EmailSender):
    def __init__(
        self,
        *,
        host: str,
        port: int = 587,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
        from_addr: str | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.from_addr = from_addr or username or "noreply@example.com"

    def send(self, to: str, subject: str, body: str) -> None:
        if not self.host:
            raise ValueError("SMTP host is required")

        message = EmailMessage()
        message["From"] = self.from_addr
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        with smtplib.SMTP(self.host, self.port, timeout=15) as server:
            if self.use_tls:
                server.starttls()
            if self.username and self.password:
                server.login(self.username, self.password)
            server.send_message(message)

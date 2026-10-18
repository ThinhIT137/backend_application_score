from __future__ import annotations

from typing import Callable

from src.models.ho_so import NguyenVongSinhVien
from src.services.adapters.email_sender import EmailSender, MockEmailSender


class NotificationService:
    def __init__(
        self,
        sender: EmailSender | None = None,
        get_email_thi_sinh: Callable[[str], str | None] | None = None,
    ) -> None:
        self.sender = sender or MockEmailSender()
        self.email_resolver = get_email_thi_sinh

    @staticmethod
    def build_subject(record: NguyenVongSinhVien) -> str:
        return f"Kết quả hồ sơ {record.ma_ho_so} - {record.ma_chuong_trinh}"

    @staticmethod
    def build_body(record: NguyenVongSinhVien) -> str:
        ket_qua = record.ket_qua or "Chưa có kết quả"
        return (
            "Kính gửi thí sinh,\n\n"
            f"Hồ sơ {record.ma_ho_so} thuộc chương trình {record.ma_chuong_trinh} "
            f"đã có kết quả: {ket_qua}.\n\n"
            "Vui lòng tra cứu thông tin chi tiết trên hệ thống tuyển sinh."
        )

    def send_for_records(
        self,
        records: list[NguyenVongSinhVien],
        *,
        get_email_thi_sinh: Callable[[str], str | None] | None = None,
    ) -> dict[str, object]:
        report = {
            "tong": len(records),
            "da_gui": 0,
            "thieu_email": 0,
            "loi": 0,
            "ma_ho_so_loi": [],
        }

        resolver = get_email_thi_sinh or self.email_resolver
        if resolver is None:
            resolver = lambda _cccd: None

        for record in records:
            try:
                email = (resolver(record.cccd) or "").strip()
            except Exception:
                report["loi"] = int(report["loi"]) + 1
                report["ma_ho_so_loi"].append(record.ma_ho_so)
                continue
            if not email:
                report["thieu_email"] = int(report["thieu_email"]) + 1
                continue

            try:
                self.sender.send(email, self.build_subject(record), self.build_body(record))
                report["da_gui"] = int(report["da_gui"]) + 1
            except Exception:
                report["loi"] = int(report["loi"]) + 1
                report["ma_ho_so_loi"].append(record.ma_ho_so)

        return report

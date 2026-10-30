"""Nhật ký bền vững để hoàn tác đúng lần nộp, không xóa dữ liệu CCCD cũ."""
from datetime import datetime
from sqlalchemy import String, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from src.core.database import Base


class SubmissionOperation(Base):
    __tablename__ = "submission_operation"
    operation_id: Mapped[str] = mapped_column(String, primary_key=True)
    cccd: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    dossier_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    payload_hash: Mapped[str] = mapped_column(String, nullable=False)
    journal: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

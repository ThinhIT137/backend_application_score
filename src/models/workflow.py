from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from src.core.database import Base


class NotificationOutbox(Base):
    __tablename__ = "admission_notification"
    ma_ho_so: Mapped[str] = mapped_column(ForeignKey("nguyen_vong_sinh_vien.ma_ho_so"), primary_key=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ScoreImportLog(Base):
    __tablename__ = "admission_score_import"
    digest: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String)
    year: Mapped[int] = mapped_column(Integer)
    admin_id: Mapped[str] = mapped_column(ForeignKey("admin.ma_admin"))
    row_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

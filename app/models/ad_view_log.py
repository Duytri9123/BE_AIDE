"""Model lưu lịch sử xem quảng cáo và số lần tải file của người dùng."""
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime, Boolean
from datetime import datetime, timezone
from .base import Base, TimestampMixin


class AdViewLog(Base, TimestampMixin):
    __tablename__ = "ad_view_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    # Số file đã tải SAU lần xem quảng cáo này
    download_count_after: Mapped[int] = mapped_column(Integer, default=0)
    # Tổng file đã tải của user tại thời điểm xem quảng cáo
    total_downloads_at_view: Mapped[int] = mapped_column(Integer, default=0)
    # Loại quảng cáo: first_visit / periodic
    ad_type: Mapped[str] = mapped_column(String(50), default="first_visit")
    # Đã hoàn thành xem chưa (người dùng bấm "Đã xem / Bỏ qua")
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

"""Compact transactional read model for saved takeoff history."""
from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AnalysisSummary(Base):
    __tablename__ = 'analysis_summaries'
    __table_args__ = (
        Index('ix_summary_session_status_created_id', 'session_id', 'status', 'created_at', 'id'),
    )

    id: Mapped[int] = mapped_column(ForeignKey('analysis_iterations.id', ondelete='CASCADE'), primary_key=True)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    iteration_number: Mapped[int] = mapped_column(Integer, nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(100), nullable=False)
    user_message: Mapped[str | None] = mapped_column(Text)
    files_analyzed: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    has_devices: Mapped[bool] = mapped_column(Boolean, nullable=False)
    devices: Mapped[list] = mapped_column(JSON, nullable=False)
    display_devices: Mapped[list] = mapped_column(JSON, nullable=False)
    confidence: Mapped[dict] = mapped_column(JSON, nullable=False)

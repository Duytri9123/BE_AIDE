"""Lossless compressed read copy; original analysis rows remain authoritative."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class AnalysisPayload(Base):
    __tablename__ = 'analysis_payloads'
    id: Mapped[int] = mapped_column(ForeignKey('analysis_iterations.id', ondelete='CASCADE'), primary_key=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

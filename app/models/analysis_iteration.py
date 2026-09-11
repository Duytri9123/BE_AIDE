from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Integer, JSON, Text, UUID
from typing import Any, Dict, Optional
import uuid
from .base import Base, TimestampMixin

class AnalysisIteration(Base, TimestampMixin):
    __tablename__ = "analysis_iterations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversation_sessions.id", ondelete="CASCADE"), index=True)
    iteration_number: Mapped[int] = mapped_column(Integer, default=1)
    trigger_type: Mapped[str] = mapped_column(String(100))
    user_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_corrections: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    focus_zone: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    prompt_sent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    files_analyzed: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ai_raw_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_parsed_devices: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ai_thinking: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    be_validation_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    devices_after_validation: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    confidence_scores: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="completed")

    session: Mapped["ConversationSession"] = relationship("ConversationSession", back_populates="iterations")

    def __str__(self) -> str:
        return f"<AnalysisIteration(id={self.id}, session_id={self.session_id}, iteration={self.iteration_number})>"

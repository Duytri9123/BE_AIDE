from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Integer, DateTime, UUID
from datetime import datetime
from typing import List, Optional
import uuid
from .base import Base, TimestampMixin

class ConversationSession(Base, TimestampMixin):
    __tablename__ = "conversation_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    total_iterations: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    finalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship("Project", back_populates="conversation_sessions")
    user: Mapped["User"] = relationship("User", back_populates="conversation_sessions")
    iterations: Mapped[List["AnalysisIteration"]] = relationship("AnalysisIteration", back_populates="session")

    def __str__(self) -> str:
        return f"<ConversationSession(id={self.id}, project_id={self.project_id}, status='{self.status}')>"

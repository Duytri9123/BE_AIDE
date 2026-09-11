from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, JSON, UUID, Integer, DateTime
from typing import Any, Dict, Optional
from datetime import datetime
import uuid
from .base import Base, TimestampMixin

class AiConnection(Base, TimestampMixin):
    __tablename__ = "ai_connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(255), index=True, default="google")
    auth_type: Mapped[str] = mapped_column(String(50), default="api_key")
    name: Mapped[str] = mapped_column(String(255), default="Chính (Default Key)")
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    api_key: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    selected_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    tag: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default="DB Account")
    quotas: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    # Connection rotation: số 1 = ưu tiên cao nhất, tiếp theo là 2, 3...
    priority: Mapped[int] = mapped_column(Integer, default=1, index=True)
    # Thời điểm lỗi gần nhất (để admin theo dõi sức khoẻ pool)
    last_error_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    def __str__(self) -> str:
        return f"<AiConnection(provider='{self.provider}', name='{self.name}', model='{self.selected_model}', priority={self.priority})>"

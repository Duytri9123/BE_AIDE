from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, Integer, ForeignKey
from .base import Base, TimestampMixin

class AiProviderModel(Base, TimestampMixin):
    __tablename__ = "ai_provider_models"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    provider_id: Mapped[str] = mapped_column(String(255), ForeignKey("ai_providers.id", ondelete="CASCADE"), index=True)
    model_key: Mapped[str] = mapped_column(String(255), index=True)
    label: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    provider: Mapped["AiProvider"] = relationship("AiProvider", back_populates="models")

    def __str__(self) -> str:
        return f"<AiProviderModel(id={self.id}, provider_id={self.provider_id}, model_key='{self.model_key}')>"

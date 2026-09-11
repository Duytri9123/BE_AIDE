from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign
from sqlalchemy import String, Boolean, Integer
from typing import List, Optional
from .base import Base, TimestampMixin

class AiProvider(Base, TimestampMixin):
    __tablename__ = "ai_providers"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    icon: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    learn_more_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    api_type: Mapped[str] = mapped_column(String(100), default="openai_compatible")
    base_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    models: Mapped[List["AiProviderModel"]] = relationship(
        "AiProviderModel", 
        back_populates="provider",
        cascade="all, delete, delete-orphan",
        lazy="selectin"
    )

    connections: Mapped[List["AiConnection"]] = relationship(
        "AiConnection",
        primaryjoin="foreign(AiConnection.provider) == AiProvider.id",
        lazy="selectin",
        viewonly=True
    )

    def __str__(self) -> str:
        return f"<AiProvider(id={self.id}, slug='{self.slug}', name='{self.name}')>"

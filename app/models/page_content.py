from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, Text
from typing import Optional
from .base import Base, TimestampMixin

class PageContent(Base, TimestampMixin):
    __tablename__ = "page_contents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    meta_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False)

    def __str__(self) -> str:
        return f"<PageContent(id={self.id}, slug='{self.slug}')>"

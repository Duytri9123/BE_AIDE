from typing import Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class Article(Base, TimestampMixin):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_html: Mapped[str] = mapped_column(Text, default="")
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    meta_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(2000), unique=True, nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    def __str__(self) -> str:
        return self.title

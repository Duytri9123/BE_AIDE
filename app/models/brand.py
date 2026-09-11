from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String
from typing import List
from .base import Base, TimestampMixin

class Brand(Base, TimestampMixin):
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    series: Mapped[List["DeviceSeries"]] = relationship("DeviceSeries", back_populates="brand")

    def __str__(self) -> str:
        return f"<Brand(id={self.id}, name='{self.name}')>"

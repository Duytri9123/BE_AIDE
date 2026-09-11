from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String
from typing import List
from .base import Base, TimestampMixin

class DeviceCategory(Base, TimestampMixin):
    __tablename__ = "device_categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    series: Mapped[List["DeviceSeries"]] = relationship("DeviceSeries", back_populates="category")

    def __str__(self) -> str:
        return f"<DeviceCategory(id={self.id}, name='{self.name}')>"

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey
from typing import List, Optional
from .base import Base, TimestampMixin

class DeviceSeries(Base, TimestampMixin):
    __tablename__ = "device_series"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), index=True)
    device_category_id: Mapped[int] = mapped_column(ForeignKey("device_categories.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    brand: Mapped["Brand"] = relationship("Brand", back_populates="series")
    category: Mapped["DeviceCategory"] = relationship("DeviceCategory", back_populates="series")
    models: Mapped[List["DeviceModel"]] = relationship("DeviceModel", back_populates="series")

    def __str__(self) -> str:
        return f"<DeviceSeries(id={self.id}, name='{self.name}')>"

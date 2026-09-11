from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, JSON, Float
from typing import Any, Dict, Optional
from .base import Base, TimestampMixin

class DeviceModel(Base, TimestampMixin):
    __tablename__ = "device_models"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    device_series_id: Mapped[int] = mapped_column(ForeignKey("device_series.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    sku: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    dimensions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    discount_pct: Mapped[float] = mapped_column(Float, default=0.0)

    series: Mapped["DeviceSeries"] = relationship("DeviceSeries", back_populates="models")

    def __str__(self) -> str:
        return f"<DeviceModel(id={self.id}, sku='{self.sku}', name='{self.name}')>"

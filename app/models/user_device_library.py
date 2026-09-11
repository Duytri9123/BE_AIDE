from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Float
from typing import Optional
from .base import Base, TimestampMixin

class UserDeviceLibrary(Base, TimestampMixin):
    __tablename__ = "user_device_libraries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    brand: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    code: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    spec: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)

    user: Mapped["User"] = relationship("User", back_populates="device_libraries")

    def __str__(self) -> str:
        return f"<UserDeviceLibrary(id={self.id}, user_id={self.user_id}, code='{self.code}')>"

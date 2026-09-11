from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, Integer, Float
from typing import List, Optional
from .base import Base, TimestampMixin

class Plan(Base, TimestampMixin):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    token_amount: Mapped[int] = mapped_column(Integer, default=0)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    duration_months: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    subscriptions: Mapped[List["Subscription"]] = relationship("Subscription", back_populates="plan", cascade="all, delete-orphan", passive_deletes=True)
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="plan")

    def __str__(self) -> str:
        return f"<Plan(id={self.id}, name='{self.name}')>"

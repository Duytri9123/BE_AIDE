from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey, Integer
from typing import Optional
from .base import Base, TimestampMixin

class TokenLog(Base, TimestampMixin):
    __tablename__ = "token_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount_changed: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="token_logs")

    def __str__(self) -> str:
        return f"<TokenLog(id={self.id}, user_id={self.user_id}, amount_changed={self.amount_changed})>"

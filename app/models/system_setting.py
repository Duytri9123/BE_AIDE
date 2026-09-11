from sqlalchemy.orm import Mapped, mapped_column, Session
from sqlalchemy import String, JSON, Text
from typing import Any, Optional
from .base import Base, TimestampMixin

class SystemSetting(Base, TimestampMixin):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    @classmethod
    def get_setting(cls, db: Session, key: str, default: Any = None) -> Any:
        setting = db.query(cls).filter(cls.key == key).first()
        return setting.value if setting else default

    def __str__(self) -> str:
        return f"<SystemSetting(id={self.id}, key='{self.key}')>"

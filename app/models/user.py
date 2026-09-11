from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, DateTime
from datetime import datetime
from typing import List, Optional
from .base import Base, TimestampMixin, SoftDeleteMixin

class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    hashed_password: Mapped[str] = mapped_column("password", String(255))
    status: Mapped[str] = mapped_column(String(50), default="active")
    tokens: Mapped[int] = mapped_column(Integer, default=1000000)
    role: Mapped[str] = mapped_column(String(50), default="user")
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def is_active(self) -> bool:
        return self.status == "active"

    @property
    def is_superuser(self) -> bool:
        return self.role == "admin"

    profile: Mapped["UserProfile"] = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan", passive_deletes=True)
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    projects: Mapped[List["Project"]] = relationship("Project", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    device_libraries: Mapped[List["UserDeviceLibrary"]] = relationship("UserDeviceLibrary", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    library_files: Mapped[List["UserLibraryFile"]] = relationship("UserLibraryFile", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    subscriptions: Mapped[List["Subscription"]] = relationship("Subscription", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    token_logs: Mapped[List["TokenLog"]] = relationship("TokenLog", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    activity_logs: Mapped[List["ActivityLog"]] = relationship("ActivityLog", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)
    conversation_sessions: Mapped[List["ConversationSession"]] = relationship("ConversationSession", back_populates="user", cascade="all, delete-orphan", passive_deletes=True)

    def __str__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey
from typing import List, Optional
from .base import Base, TimestampMixin, SoftDeleteMixin

class Project(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="projects")
    versions: Mapped[List["ProjectVersion"]] = relationship("ProjectVersion", back_populates="project", cascade="all, delete-orphan", passive_deletes=True)
    files: Mapped[List["ProjectFile"]] = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan", passive_deletes=True)
    conversation_sessions: Mapped[List["ConversationSession"]] = relationship("ConversationSession", back_populates="project", cascade="all, delete-orphan", passive_deletes=True)

    def __str__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}')>"

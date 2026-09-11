from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, Boolean
from typing import Optional
from .base import Base, TimestampMixin

class ProjectFile(Base, TimestampMixin):
    __tablename__ = "project_files"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    project_version_id: Mapped[Optional[int]] = mapped_column(ForeignKey("project_versions.id", ondelete="CASCADE"), nullable=True, index=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(1000))
    file_type: Mapped[str] = mapped_column(String(50))
    file_size: Mapped[int] = mapped_column(Integer)
    is_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)

    project: Mapped["Project"] = relationship("Project", back_populates="files")
    project_version: Mapped[Optional["ProjectVersion"]] = relationship("ProjectVersion", back_populates="files")

    def __str__(self) -> str:
        return f"<ProjectFile(id={self.id}, filename='{self.filename}')>"

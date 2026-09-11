from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, JSON
from typing import List, Optional, Any, Dict
from .base import Base, TimestampMixin

class ProjectVersion(Base, TimestampMixin):
    __tablename__ = "project_versions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    pdf_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    devices: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    graph: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    layout: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")

    project: Mapped["Project"] = relationship("Project", back_populates="versions")
    files: Mapped[List["ProjectFile"]] = relationship("ProjectFile", back_populates="project_version")

    def __str__(self) -> str:
        return f"<ProjectVersion(id={self.id}, project_id={self.project_id}, version={self.version_number})>"

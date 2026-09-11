from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey
from .base import Base, TimestampMixin

class UserLibraryFile(Base, TimestampMixin):
    __tablename__ = "user_library_files"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column("file_name", String(255))
    file_path: Mapped[str] = mapped_column(String(1000))
    file_type: Mapped[str] = mapped_column(String(50))
    file_size: Mapped[int] = mapped_column(Integer)

    user: Mapped["User"] = relationship("User", back_populates="library_files")

    def __str__(self) -> str:
        return f"<UserLibraryFile(id={self.id}, user_id={self.user_id}, filename='{self.filename}')>"

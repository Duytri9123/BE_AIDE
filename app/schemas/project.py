from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class ProjectCreate(BaseModel):
    name: str
    category: Optional[str] = None

class FileUploadResponse(BaseModel):
    id: UUID
    file_path: str
    file_type: str
    file_size: int

class ProjectResponse(BaseModel):
    id: UUID
    name: str
    category: Optional[str]
    created_at: datetime
    file_count: int
    item_count: int
    total_value: float
    files: List[FileUploadResponse] = []
    items: List[dict] = []

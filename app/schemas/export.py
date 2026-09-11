from pydantic import BaseModel
from typing import Optional, Union
from uuid import UUID

class ExportRequest(BaseModel):
    project_id: Union[int, str, UUID]
    scope: Optional[str] = "full"
    layout: Optional[str] = "standard"
    brand_preference: Optional[str] = None

class ExportResponse(BaseModel):
    download_url: str
    filename: str
    file_size: int

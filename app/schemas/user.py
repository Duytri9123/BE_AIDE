from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID

class UserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    phone: Optional[str]
    status: str
    tokens: int
    role: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None

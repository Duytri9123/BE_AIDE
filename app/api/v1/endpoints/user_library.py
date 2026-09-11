from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.models.user_library_file import UserLibraryFile
from app.api.deps import get_current_active_user
from app.db.session import get_db
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import aiofiles
import os
from pathlib import Path
from app.core.config import settings

router = APIRouter()

class LibraryFileResponse(BaseModel):
    id: int
    filename: str
    file_path: str
    file_size: int
    file_type: str
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/files", response_model=List[LibraryFileResponse])
async def list_files(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Danh sách files trong library của user"""
    stmt = select(UserLibraryFile).where(UserLibraryFile.user_id == current_user.id)
    result = await db.execute(stmt)
    files = result.scalars().all()
    return files

@router.post("/files", response_model=LibraryFileResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Upload file vào library"""
    # Tạo thư mục upload nếu chưa có
    upload_dir = Path(getattr(settings, "USER_LIBRARY_DIR", "storage/user_library")) / str(current_user.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Lưu file
    file_path = upload_dir / file.filename
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
    
    file_size = os.path.getsize(file_path)
    
    # Lưu vào database
    library_file = UserLibraryFile(
        user_id=current_user.id,
        filename=file.filename,
        file_path=str(file_path),
        file_size=file_size,
        file_type=file.content_type or "application/octet-stream"
    )
    
    db.add(library_file)
    await db.commit()
    await db.refresh(library_file)
    
    return library_file

@router.delete("/files/{file_id}")
async def delete_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Xóa file khỏi library"""
    stmt = select(UserLibraryFile).where(
        UserLibraryFile.id == file_id,
        UserLibraryFile.user_id == current_user.id
    )
    result = await db.execute(stmt)
    library_file = result.scalar_one_or_none()
    
    if not library_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Xóa file vật lý
    if os.path.exists(library_file.file_path):
        os.remove(library_file.file_path)
    
    # Xóa khỏi database
    await db.delete(library_file)
    await db.commit()
    
    return {"message": "File deleted successfully"}

@router.get("/files/{file_id}", response_model=LibraryFileResponse)
async def get_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Chi tiết file"""
    stmt = select(UserLibraryFile).where(
        UserLibraryFile.id == file_id,
        UserLibraryFile.user_id == current_user.id
    )
    result = await db.execute(stmt)
    library_file = result.scalar_one_or_none()
    
    if not library_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    return library_file

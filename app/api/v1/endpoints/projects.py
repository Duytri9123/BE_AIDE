from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.models.user import User
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.api.deps import get_current_active_user
from pydantic import BaseModel, field_serializer
from typing import List, Optional
from datetime import datetime, timezone
import aiofiles
import os
import re
from pathlib import Path
import ezdxf
from app.core.config import settings

router = APIRouter()

class ProjectResponse(BaseModel):
    id: int
    name: str
    category: Optional[str]
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    file_count: int = 0
    device_count: int = 0
    total_value: float = 0
    
    @field_serializer('created_at', 'updated_at', mode='plain')
    def serialize_dt(self, v: Optional[datetime]) -> Optional[str]:
        if v is None:
            return None
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()
    
    class Config:
        from_attributes = True

class ProjectCreate(BaseModel):
    name: str
    category: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None

class BlankCadCreate(BaseModel):
    filename: str

class ProjectFileResponse(BaseModel):
    id: int
    project_id: int
    filename: str
    file_path: str
    file_size: int
    file_type: str
    is_generated: Optional[bool] = False
    created_at: datetime
    
    @field_serializer('created_at', mode='plain')
    def serialize_dt(self, v: Optional[datetime]) -> Optional[str]:
        if v is None:
            return None
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()
    
    class Config:
        from_attributes = True

class ProjectStatsResponse(BaseModel):
    total_projects: int
    total_files: int
    total_devices: int
    total_value: float

async def get_project_or_404(project_id: int, db: AsyncSession, current_user: User) -> Project:
    query = select(Project).where(Project.id == project_id, Project.deleted_at == None)
    if not current_user.is_superuser:
        query = query.where(Project.user_id == current_user.id)
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_active_user)
):
    """Danh sách projects của user (hoặc tất cả nếu là admin) - dự án mới cập nhật nhất lên đầu"""
    query = select(Project).where(Project.deleted_at == None)
    if not current_user.is_superuser:
        query = query.where(Project.user_id == current_user.id)
    query = query.order_by(
        func.coalesce(Project.updated_at, Project.created_at).desc(),
        Project.id.desc()
    )
    stmt = query.offset(skip).limit(limit)
    result = await db.execute(stmt)
    projects = result.scalars().all()
    
    # Enrich with counts
    enriched_projects = []
    for project in projects:
        # Count files
        file_stmt = select(func.count(ProjectFile.id)).where(ProjectFile.project_id == project.id)
        file_result = await db.execute(file_stmt)
        file_count = file_result.scalar() or 0
        
        project_dict = {
            "id": project.id,
            "name": project.name,
            "category": project.category,
            "user_id": project.user_id,
            "created_at": project.created_at,
            "updated_at": project.updated_at or project.created_at,
            "file_count": file_count,
            "device_count": 0,
            "total_value": 0.0,
        }
        enriched_projects.append(ProjectResponse(**project_dict))
    
    return enriched_projects

@router.get("/stats", response_model=ProjectStatsResponse)
async def get_project_stats(
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_active_user)
):
    """Thống kê tổng quan projects của user"""
    proj_query = select(func.count(Project.id)).where(Project.deleted_at == None)
    file_query = select(func.count(ProjectFile.id)).join(
        Project, ProjectFile.project_id == Project.id
    ).where(Project.deleted_at == None)
    if not current_user.is_superuser:
        proj_query = proj_query.where(Project.user_id == current_user.id)
        file_query = file_query.where(Project.user_id == current_user.id)

    project_result = await db.execute(proj_query)
    total_projects = project_result.scalar() or 0
    
    file_result = await db.execute(file_query)
    total_files = file_result.scalar() or 0
    
    return ProjectStatsResponse(
        total_projects=total_projects,
        total_files=total_files,
        total_devices=0,
        total_value=0.0,
    )

@router.post("", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_active_user)
):
    """Tạo project mới (kiểm tra không trùng tên)"""
    name = project.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Tên dự án không được để trống")

    # Kiểm tra trùng tên dự án
    check_stmt = select(Project).where(
        Project.user_id == current_user.id,
        Project.deleted_at == None,
        func.lower(func.trim(Project.name)) == name.lower()
    )
    check_res = await db.execute(check_stmt)
    if check_res.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Tên dự án '{name}' đã tồn tại. Vui lòng chọn tên khác."
        )

    new_project = Project(
        name=name,
        category=project.category,
        user_id=current_user.id
    )
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)

    try:
        from app.services.activity_logger import log_activity
        await log_activity(
            db=db,
            action=f"Tạo dự án mới: '{new_project.name}'",
            user_id=current_user.id,
            entity_type="Dự án",
            entity_id=str(new_project.id),
            details={"project_name": new_project.name, "category": new_project.category or "Tủ điện"},
            create_notification=True,
            notification_title="Dự án mới được tạo",
            notification_body=f"Dự án '{new_project.name}' vừa được tạo bởi {current_user.name or current_user.email}",
            notification_type="new-project",
            notification_link="/admin/project/list"
        )
    except Exception as e:
        logger.warning(f"Lỗi log hoạt động tạo dự án: {e}")

    return new_project

@router.get("/{id}", response_model=ProjectResponse)
async def get_project(
    id: int, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_active_user)
):
    """Chi tiết project"""
    return await get_project_or_404(id, db, current_user)

@router.put("/{id}", response_model=ProjectResponse)
async def update_project(
    id: int,
    project_update: ProjectUpdate,
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_active_user)
):
    """Cập nhật project (kiểm tra không trùng tên)"""
    project = await get_project_or_404(id, db, current_user)
    
    if project_update.name is not None:
        name = project_update.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Tên dự án không được để trống")
        
        # Kiểm tra trùng tên với dự án khác
        check_stmt = select(Project).where(
            Project.user_id == current_user.id,
            Project.deleted_at == None,
            Project.id != id,
            func.lower(func.trim(Project.name)) == name.lower()
        )
        check_res = await db.execute(check_stmt)
        if check_res.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Tên dự án '{name}' đã tồn tại. Vui lòng chọn tên khác."
            )
        project.name = name

    if project_update.category is not None:
        project.category = project_update.category
    
    from datetime import datetime, timezone
    project.updated_at = datetime.now(timezone.utc)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project

@router.delete("/{id}")
async def delete_project(
    id: int, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_active_user)
):
    """Xóa project (soft delete)"""
    project = await get_project_or_404(id, db, current_user)
    
    from datetime import datetime, timezone
    project.deleted_at = datetime.now(timezone.utc)
    project.updated_at = datetime.now(timezone.utc)
    db.add(project)
    await db.commit()
    
    return {"message": "Project deleted successfully"}

@router.post("/{id}/upload", response_model=ProjectFileResponse)
async def upload_project_file(
    id: int, 
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_active_user)
):
    """Upload file cho project"""
    project = await get_project_or_404(id, db, current_user)
    
    # Tạo thư mục upload
    upload_dir = Path(getattr(settings, "PROJECTS_DIR", "storage/projects")) / str(id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Lưu file
    file_path = upload_dir / file.filename
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
    
    file_size = os.path.getsize(file_path)
    
    # Kiểm tra xem file đã tồn tại trong DB chưa để tránh tạo bản ghi trùng lặp
    existing_stmt = select(ProjectFile).where(
        ProjectFile.project_id == id,
        ProjectFile.filename == file.filename
    )
    existing_res = await db.execute(existing_stmt)
    existing_file = existing_res.scalar_one_or_none()

    from datetime import datetime, timezone
    now_utc = datetime.now(timezone.utc)
    project.updated_at = now_utc
    db.add(project)

    if existing_file:
        existing_file.file_path = str(file_path)
        existing_file.file_size = file_size
        existing_file.file_type = file.content_type or "application/octet-stream"
        existing_file.created_at = now_utc
        await db.commit()
        await db.refresh(existing_file)
        return existing_file

    # Lưu vào database
    project_file = ProjectFile(
        project_id=id,
        filename=file.filename,
        file_path=str(file_path),
        file_size=file_size,
        file_type=file.content_type or "application/octet-stream",
        created_at=now_utc
    )
    
    db.add(project_file)
    await db.commit()
    await db.refresh(project_file)

    try:
        from app.services.activity_logger import log_activity
        await log_activity(
            db=db,
            action=f"Tải lên bản vẽ: {project_file.filename}",
            user_id=current_user.id,
            entity_type="Tập tin",
            entity_id=str(project_file.id),
            details={"filename": project_file.filename, "file_size": file_size, "project_name": project.name},
            create_notification=True,
            notification_title="Tập tin bản vẽ mới",
            notification_body=f"Bản vẽ '{project_file.filename}' tải lên dự án '{project.name}' bởi {current_user.name or current_user.email}",
            notification_type="file-uploaded",
            notification_link="/admin/project-file/list"
        )
    except Exception as e:
        logger.warning(f"Lỗi log upload file: {e}")

    return project_file


@router.post("/{id}/cad/blank", response_model=ProjectFileResponse)
async def create_blank_cad_file(
    id: int,
    payload: BlankCadCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Tạo một bản vẽ kỹ thuật DXF trống để người dùng vẽ trực tiếp."""
    project = await get_project_or_404(id, db, current_user)

    drawing_name = payload.filename.strip()
    if drawing_name.lower().endswith(".dxf"):
        drawing_name = drawing_name[:-4].strip()

    if not drawing_name:
        raise HTTPException(status_code=400, detail="Tên bản vẽ không được để trống")
    if len(drawing_name) > 120:
        raise HTTPException(status_code=400, detail="Tên bản vẽ không được vượt quá 120 ký tự")
    if re.search(r'[<>:"/\\|?*\x00-\x1f]', drawing_name):
        raise HTTPException(status_code=400, detail="Tên bản vẽ chứa ký tự không hợp lệ")
    if drawing_name.endswith((".", " ")):
        raise HTTPException(status_code=400, detail="Tên bản vẽ không được kết thúc bằng dấu chấm hoặc khoảng trắng")
    if drawing_name.split(".", 1)[0].upper() in {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }:
        raise HTTPException(status_code=400, detail="Tên bản vẽ này được hệ điều hành dành riêng")

    filename = f"{drawing_name}.dxf"
    existing_stmt = select(ProjectFile).where(
        ProjectFile.project_id == id,
        func.lower(ProjectFile.filename) == filename.lower(),
    )
    if (await db.execute(existing_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Bản vẽ '{filename}' đã tồn tại")

    output_dir = Path(getattr(settings, "PROJECTS_DIR", "storage/projects")) / str(id)
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / filename
    if file_path.exists():
        raise HTTPException(status_code=400, detail=f"Bản vẽ '{filename}' đã tồn tại")

    try:
        document = ezdxf.new("R2010", setup=True)
        document.header["$INSUNITS"] = 4  # millimetres
        document.saveas(file_path)

        now_utc = datetime.now(timezone.utc)
        project.updated_at = now_utc
        project_file = ProjectFile(
            project_id=id,
            filename=filename,
            file_path=str(file_path),
            file_size=os.path.getsize(file_path),
            file_type="application/dxf",
            is_generated=True,
            created_at=now_utc,
        )
        db.add(project)
        db.add(project_file)
        await db.commit()
        await db.refresh(project_file)
        return project_file
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail="Không thể tạo bản vẽ CAD trống") from exc

@router.get("/{id}/files", response_model=List[ProjectFileResponse])
async def list_project_files(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Danh sách files của project - file mới nhất lên đầu"""
    await get_project_or_404(id, db, current_user)
    
    # Lấy files sắp xếp mới nhất lên đầu
    stmt = select(ProjectFile).where(ProjectFile.project_id == id).order_by(ProjectFile.created_at.desc(), ProjectFile.id.desc())
    result = await db.execute(stmt)
    files = result.scalars().all()
    
    return files

@router.delete("/{id}/files/{file_id}")
async def delete_project_file(
    id: int, 
    file_id: int, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_active_user)
):
    """Xóa file của project"""
    project = await get_project_or_404(id, db, current_user)
    
    # Lấy file
    stmt = select(ProjectFile).where(
        ProjectFile.id == file_id,
        ProjectFile.project_id == id
    )
    result = await db.execute(stmt)
    project_file = result.scalar_one_or_none()
    
    if not project_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Xóa file vật lý
    if os.path.exists(project_file.file_path):
        os.remove(project_file.file_path)
    
    # Xóa khỏi database
    await db.delete(project_file)
    
    from datetime import datetime, timezone
    project.updated_at = datetime.now(timezone.utc)
    db.add(project)
    await db.commit()
    
    return {"message": "File deleted successfully"}


@router.get("/{id}/files/{file_id}/download")
async def download_project_file(
    id: int,
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Download / stream file của project"""
    await get_project_or_404(id, db, current_user)
        
    stmt = select(ProjectFile).where(
        ProjectFile.id == file_id,
        ProjectFile.project_id == id
    )
    result = await db.execute(stmt)
    project_file = result.scalar_one_or_none()
    if not project_file or not os.path.exists(project_file.file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    from fastapi.responses import FileResponse
    return FileResponse(
        path=project_file.file_path,
        filename=project_file.filename,
        media_type=project_file.file_type or "application/octet-stream"
    )

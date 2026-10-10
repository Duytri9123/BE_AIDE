from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.user import User
from app.core.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không thể xác thực thông tin đăng nhập",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id or payload.get('type') == 'refresh':
        raise credentials_exception
    
    try:
        stmt = select(User).where(User.id == int(user_id))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
    except Exception:
        raise credentials_exception
        
    if not user:
        raise credentials_exception
        
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Tài khoản không hoạt động")
    return current_user

async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if current_user.role != "admin" and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập quản trị")
    return current_user

async def get_current_admin_session_or_token(request: Request, db=Depends(get_db)):
    """Admin helpers support the signed admin session and verified bearer tokens."""
    authorization = request.headers.get('authorization', '')
    if authorization.lower().startswith('bearer '):
        user = await get_current_user(db=db, token=authorization.split(' ', 1)[1])
    else:
        identity = request.scope.get('session', {}).get('token')
        if not identity:
            raise HTTPException(401, 'Đăng nhập quản trị để tiếp tục.')
        try:
            user = (await db.execute(select(User).where(User.id == int(identity)))).scalar_one_or_none()
        except (TypeError, ValueError):
            raise HTTPException(401, 'Phiên quản trị không hợp lệ.')
    if not user or not user.is_active or not (user.is_superuser or user.role == 'admin'):
        raise HTTPException(403, 'Không có quyền truy cập quản trị.')
    return user

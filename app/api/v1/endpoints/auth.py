import secrets
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.db.session import get_db
from app.models.user import User
from app.models.user_profile import UserProfile
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token
from pydantic import BaseModel, EmailStr
import os
from typing import Optional
from app.services.auth.otp_service import OTPService

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class SendOtpRequest(BaseModel):
    email: EmailStr
    purpose: Optional[str] = "register"

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None
    otp: Optional[str] = None

class GoogleAuthRequest(BaseModel):
    credential: Optional[str] = None
    token: Optional[str] = None
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    picture: Optional[str] = None

class TokenResponse(BaseModel):
    token: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    avatar_url: Optional[str] = None

@router.post("/send-otp")
async def send_otp(request: SendOtpRequest, db: AsyncSession = Depends(get_db)):
    """Gửi mã xác thực OTP 6 số đến Gmail người dùng."""
    clean_email = request.email.lower().strip()

    # Nếu gửi OTP cho mục đích đăng ký tài khoản, kiểm tra trùng email
    if request.purpose == "register":
        stmt = select(User).where(User.email == clean_email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email này đã được đăng ký tài khoản trong hệ thống. Vui lòng đăng nhập!",
            )

    success, message, dev_otp = OTPService.send_otp(clean_email)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    response_data = {"message": message, "email": clean_email}
    if os.getenv("DEBUG", "true").lower() == "true" and dev_otp:
        response_data["dev_otp"] = dev_otp

    return response_data

@router.post("/register")
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    clean_email = request.email.lower().strip()

    # Kiểm tra mã OTP bắt buộc khi đăng ký email
    if not request.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng nhập mã xác thực OTP được gửi đến hòm thư Gmail của bạn.",
        )

    if not OTPService.verify_otp(clean_email, request.otp):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã OTP không chính xác hoặc đã hết hạn. Vui lòng kiểm tra lại Gmail hoặc gửi lại mã mới!",
        )

    stmt = select(User).where(User.email == clean_email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email đã được đăng ký trong hệ thống",
        )

    user = User(
        email=clean_email,
        name=request.name.strip() if request.name else clean_email.split("@")[0],
        hashed_password=get_password_hash(request.password),
        status="active",
        role="user",
        tokens=1000000,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    try:
        from app.services.activity_logger import log_activity
        await log_activity(
            db=db,
            action=f"Người dùng mới đăng ký: {user.name or user.email}",
            user_id=user.id,
            entity_type="Người dùng",
            entity_id=str(user.id),
            details={"email": user.email, "role": user.role},
            create_notification=True,
            notification_title="Người dùng mới đăng ký",
            notification_body=f"Kỹ sư điện {user.name or user.email} vừa đăng ký tài khoản",
            notification_type="new-user",
            notification_link="/admin/user/list"
        )
    except Exception as e:
        logger.warning(f"Lỗi log hoạt động đăng ký: {e}")

    return {
        "message": "Đăng ký tài khoản thành công",
        "user_id": user.id,
        "email": user.email,
    }

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    login_identifier = request.email.strip()
    # Support login with either email or name
    stmt = select(User).where(
        or_(
            User.email == login_identifier.lower(),
            User.name == login_identifier
        )
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email/Tên đăng nhập hoặc mật khẩu không chính xác",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tài khoản của bạn đã bị vô hiệu hóa",
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return {
        "token": access_token,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }

@router.post("/refresh")
async def refresh(refresh_token: str, db: AsyncSession = Depends(get_db)):
    payload = decode_token(refresh_token)
    user_id = payload.get("sub")
    if not user_id or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token không hợp lệ",
        )

    stmt = select(User).where(User.id == int(user_id))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Người dùng không tồn tại hoặc đã bị vô hiệu hóa",
        )

    new_access_token = create_access_token(user.id)
    return {
        "access_token": new_access_token,
        "token": new_access_token,
        "token_type": "bearer",
    }

@router.post("/logout")
async def logout():
    return {"message": "Đăng xuất thành công"}

@router.post("/google", response_model=TokenResponse)
async def google_auth(request: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """Đăng nhập hoặc tự động đăng ký qua Google OAuth ID Token."""
    email = str(request.email) if request.email else None
    name = request.name
    picture = request.picture

    # 1. Nếu có ID Token (credential từ Google Identity Services), xác thực với Google TokenInfo API
    if request.credential:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(
                    f"https://oauth2.googleapis.com/tokeninfo?id_token={request.credential}"
                )
                if res.status_code == 200:
                    data = res.json()
                    email = data.get("email")
                    name = data.get("name") or data.get("given_name") or (email.split("@")[0] if email else None)
                    picture = data.get("picture") or picture
        except Exception:
            pass

    # 1b. Nếu có OAuth Access Token từ popup
    if not email and request.token:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {request.token}"},
                )
                if res.status_code == 200:
                    data = res.json()
                    email = data.get("email")
                    name = data.get("name") or data.get("given_name") or (email.split("@")[0] if email else None)
                    picture = data.get("picture") or picture
        except Exception:
            pass


    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể xác thực thông tin tài khoản Google. Vui lòng thử lại!",
        )

    clean_email = email.lower().strip()

    # 2. Tìm kiếm user theo email
    stmt = select(User).where(User.email == clean_email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tài khoản của bạn đã bị vô hiệu hóa",
            )
        if not user.name and name:
            user.name = name
            await db.commit()
            await db.refresh(user)
    else:
        # 3. Tự động tạo user mới cho tài khoản Google
        random_pwd = secrets.token_urlsafe(24)
        user = User(
            email=clean_email,
            name=name or clean_email.split("@")[0],
            hashed_password=get_password_hash(random_pwd),
            status="active",
            role="user",
            tokens=1000000,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # 3b. Lưu hoặc cập nhật avatar vào UserProfile
    user_avatar = None
    try:
        stmt_prof = select(UserProfile).where(UserProfile.user_id == user.id)
        prof_res = await db.execute(stmt_prof)
        profile = prof_res.scalar_one_or_none()
        if profile:
            if picture and not profile.avatar_url:
                profile.avatar_url = picture
                await db.commit()
            user_avatar = profile.avatar_url or picture
        else:
            profile = UserProfile(
                user_id=user.id,
                full_name=user.name,
                avatar_url=picture,
            )
            db.add(profile)
            await db.commit()
            user_avatar = picture
    except Exception:
        pass

    # 4. Sinh access token và refresh token
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return {
        "token": access_token,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "avatar_url": user_avatar,
    }


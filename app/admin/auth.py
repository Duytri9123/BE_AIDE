from sqladmin.authentication import AuthenticationBackend
from fastapi import Request
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.core.security import verify_password
from app.core.config import settings
from sqlalchemy import select

class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        raw_email = form.get("username")
        password = form.get("password")
        if not raw_email or not password:
            return False

        email = raw_email.strip().lower()

        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.email.ilike(email))
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user and (user.role == "admin" or user.is_superuser):
                if verify_password(password, user.hashed_password):
                    request.session.update({"token": str(user.id)})
                    return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False
        return True

authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)

"""
Script để tạo dữ liệu mẫu ban đầu cho database
"""
import os
import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash

ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@webbaogia.com")
ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
TEST_EMAIL = os.getenv("DEFAULT_TEST_EMAIL", "test@webbaogia.com")
TEST_PASSWORD = os.getenv("DEFAULT_TEST_PASSWORD", "test123")


async def create_admin_user():
    """Tạo admin user mặc định"""
    async with AsyncSessionLocal() as session:
        try:
            # Kiểm tra xem đã có admin chưa
            stmt = select(User).where(User.email == ADMIN_EMAIL)
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print("✅ Admin user already exists")
                return existing_user
            
            # Tạo admin user mới
            admin = User(
                email=ADMIN_EMAIL,
                name="Administrator",
                hashed_password=get_password_hash(ADMIN_PASSWORD),
                role="admin",
                status="active",
                tokens=1000000,
                phone=None
            )
            
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
            
            print("✅ Admin user created successfully!")
            print(f"   Email: {ADMIN_EMAIL}")
            print(f"   ID: {admin.id}")
            
            return admin
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error creating admin user: {e}")
            import traceback
            traceback.print_exc()
            return None


async def create_test_user():
    """Tạo test user"""
    async with AsyncSessionLocal() as session:
        try:
            # Kiểm tra xem đã có test user chưa
            stmt = select(User).where(User.email == TEST_EMAIL)
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print("✅ Test user already exists")
                return existing_user
            
            # Tạo test user mới
            test_user = User(
                email=TEST_EMAIL,
                name="Test User",
                hashed_password=get_password_hash(TEST_PASSWORD),
                role="user",
                status="active",
                tokens=100000,
                phone=None
            )
            
            session.add(test_user)
            await session.commit()
            await session.refresh(test_user)
            
            print("✅ Test user created successfully!")
            print(f"   Email: {TEST_EMAIL}")
            print(f"   ID: {test_user.id}")
            
            return test_user
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error creating test user: {e}")
            import traceback
            traceback.print_exc()
            return None


async def main():
    """Chạy seed data"""
    print("=" * 60)
    print("Seeding Initial Data...")
    print("=" * 60)
    
    # Tạo admin user
    print("\n1. Creating Admin User...")
    await create_admin_user()
    
    # Tạo test user
    print("\n2. Creating Test User...")
    await create_test_user()
    
    print("\n" + "=" * 60)
    print("Seeding Complete!")
    print("=" * 60)
    print("\nYou can now login with configured credentials.")
    print(f"  Admin: {ADMIN_EMAIL}")
    print(f"  Test:  {TEST_EMAIL}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

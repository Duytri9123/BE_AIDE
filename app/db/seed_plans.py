"""
Hàm seed các gói cước mặc định cho hệ thống
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.plan import Plan

DEFAULT_PLANS = [
    {
        "name": "Gói Khởi Đầu",
        "price": 0.0,
        "token_amount": 50000,
        "duration_months": 1,
        "description": "Tạo tối đa 3 dự án\nBóc tách sơ đồ cơ bản\nXuất báo giá PDF tiêu chuẩn\nThư viện thiết bị mẫu",
        "is_active": True,
    },
    {
        "name": "Gói Kỹ Sư Chuyên Nghiệp",
        "price": 499000.0,
        "token_amount": 1000000,
        "duration_months": 1,
        "description": "Dự án không giới hạn\nBóc tách AI nhận diện đa lớp nâng cao\nXuất báo giá Excel công thức sống\nThư viện thiết bị đầy đủ các hãng\nHỗ trợ kỹ thuật ưu tiên",
        "is_active": True,
    },
    {
        "name": "Gói Doanh Nghiệp VIP",
        "price": 1499000.0,
        "token_amount": 5000000,
        "duration_months": 1,
        "description": "Toàn bộ tính năng Chuyên nghiệp\nCấp 5,000,000 Tokens/tháng\nQuản lý nhóm và phân quyền thành viên\nTùy chỉnh template báo giá doanh nghiệp\nAPI tích hợp hệ thống nội bộ\nHỗ trợ kỹ thuật 24/7",
        "is_active": True,
    },
]

async def seed_default_plans(db: AsyncSession) -> None:
    """Tự động tạo các gói cước ban đầu nếu bảng plans chưa có dữ liệu."""
    result = await db.execute(select(Plan))
    existing_plans = result.scalars().all()
    if not existing_plans:
        for item in DEFAULT_PLANS:
            plan = Plan(**item)
            db.add(plan)
        await db.commit()
        print("✅ Đã khởi tạo các gói cước mặc định thành công!")

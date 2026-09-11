from sqladmin import BaseView, expose
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, update
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.brand import Brand
from app.models.device_category import DeviceCategory
from app.models.device_series import DeviceSeries
from app.models.device_model import DeviceModel
from app.models.activity_log import ActivityLog
from app.models.notification import Notification
from app.models.token_log import TokenLog
from app.services.pusher_service import pusher_service
from app.core.config import settings
import datetime

class AnalyticsView(BaseView):
    name = "Dashboard Thống Kê"
    icon = "fa-solid fa-chart-pie"
    category = "Tổng quan"

    @expose("/analytics", methods=["GET"])
    async def analytics_page(self, request):
        async with AsyncSessionLocal() as db:
            # ── 1. STATS OVERVIEW ──────────────────────────────────────────
            total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
            total_projects = (await db.execute(select(func.count(Project.id)).where(Project.deleted_at == None))).scalar() or 0
            total_files = (await db.execute(select(func.count(ProjectFile.id)))).scalar() or 0
            
            # File size sum
            total_bytes = (await db.execute(select(func.sum(ProjectFile.file_size)))).scalar() or 0
            if total_bytes >= 1024 * 1024 * 1024:
                file_size_str = f"{total_bytes / (1024 * 1024 * 1024):.1f} GB"
            elif total_bytes >= 1024 * 1024:
                file_size_str = f"{total_bytes / (1024 * 1024):.1f} MB"
            else:
                file_size_str = f"{total_bytes / 1024:.0f} KB" if total_bytes > 0 else "0 MB"

            # Tokens consumed
            total_tokens = (await db.execute(select(func.sum(func.abs(TokenLog.amount_changed))))).scalar() or 0
            if total_tokens == 0:
                total_tokens = (await db.execute(select(func.sum(User.tokens)))).scalar() or 0
                
            if total_tokens >= 1_000_000:
                tokens_str = f"{total_tokens / 1_000_000:.1f}M"
            elif total_tokens >= 1_000:
                tokens_str = f"{total_tokens / 1_000:.0f}K"
            else:
                tokens_str = str(total_tokens)

            # Device & Brand Counts
            total_brands = (await db.execute(select(func.count(Brand.id)))).scalar() or 0
            total_models = (await db.execute(select(func.count(DeviceModel.id)))).scalar() or 0
            total_series = (await db.execute(select(func.count(DeviceSeries.id)))).scalar() or 0
            total_categories = (await db.execute(select(func.count(DeviceCategory.id)))).scalar() or 0

            # ── 2. BRAND DISTRIBUTION (HÃNG THIẾT BỊ) ──────────────────────
            brand_query = (
                select(
                    Brand.name, 
                    func.count(DeviceModel.id).label("model_count"),
                    func.count(func.distinct(DeviceSeries.id)).label("series_count")
                )
                .join(DeviceSeries, Brand.id == DeviceSeries.brand_id, isouter=True)
                .join(DeviceModel, DeviceSeries.id == DeviceModel.device_series_id, isouter=True)
                .group_by(Brand.name)
                .order_by(desc("model_count"), desc("series_count"), Brand.name)
                .limit(6)
            )
            brand_results = (await db.execute(brand_query)).all()
            
            brand_labels = []
            brand_data = []
            brand_stats = []
            
            if brand_results and any(r[1] > 0 for r in brand_results):
                total_brand_models = sum(r[1] for r in brand_results) or 1
                for r in brand_results:
                    brand_labels.append(r[0])
                    brand_data.append(r[1])
                    brand_stats.append({
                        "name": r[0],
                        "models": r[1],
                        "series": r[2] or 1,
                        "percentage": round(r[1] / total_brand_models * 100, 1)
                    })

            # ── 3. CATEGORY DISTRIBUTION (LOẠI / DANH MỤC THIẾT BỊ) ─────────
            cat_query = (
                select(DeviceCategory.name, func.count(DeviceModel.id).label("model_count"))
                .join(DeviceSeries, DeviceCategory.id == DeviceSeries.device_category_id, isouter=True)
                .join(DeviceModel, DeviceSeries.id == DeviceModel.device_series_id, isouter=True)
                .group_by(DeviceCategory.name)
                .order_by(desc("model_count"), DeviceCategory.name)
                .limit(6)
            )
            cat_results = (await db.execute(cat_query)).all()
            cat_labels = []
            cat_data = []
            
            if cat_results and any(r[1] > 0 for r in cat_results):
                for r in cat_results:
                    cat_labels.append(r[0])
                    cat_data.append(r[1])

            # ── 4. RECENT ACTIVITIES ───────────────────────────────────────
            recent_activities_result = await db.execute(
                select(ActivityLog)
                .options(selectinload(ActivityLog.user))
                .order_by(ActivityLog.created_at.desc())
                .limit(10)
            )
            recent_activities = recent_activities_result.scalars().all()
            
            activity_list = []
            now_dt = datetime.datetime.now()
            for activity in recent_activities:
                time_str = "Vừa xong"
                if activity.created_at:
                    diff_sec = (now_dt - activity.created_at).total_seconds()
                    if diff_sec < 60:
                        time_str = "Vừa xong"
                    elif diff_sec < 3600:
                        time_str = f"{int(diff_sec // 60)} phút trước"
                    elif diff_sec < 86400:
                        time_str = f"{int(diff_sec // 3600)} giờ trước"
                    else:
                        time_str = activity.created_at.strftime("%H:%M - %d/%m")

                activity_list.append({
                    "action": activity.action,
                    "user": activity.user.name if activity.user and activity.user.name else (activity.user.email if activity.user else "Hệ thống"),
                    "entity_type": activity.entity_type or "Hệ thống",
                    "time": time_str
                })

            # ── 5. ACTIVE USERS & PROJECTS ─────────────────────────────────
            active_users_result = await db.execute(
                select(User).order_by(User.created_at.desc()).limit(6)
            )
            active_users = active_users_result.scalars().all()
            
            user_list = []
            for user in active_users:
                projects_count = (await db.execute(
                    select(func.count(Project.id))
                    .where(Project.user_id == user.id, Project.deleted_at == None)
                )).scalar() or 0
                
                user_list.append({
                    "name": user.name or user.email.split("@")[0],
                    "email": user.email,
                    "role": user.role,
                    "status": user.status,
                    "tokens_used": f"{user.tokens:,}" if user.tokens else "0",
                    "projects": projects_count,
                    "initials": (user.name[:2] if user.name else user.email[:2]).upper()
                })

            stats = {
                "total_users": total_users,
                "total_projects": total_projects,
                "total_files": total_files,
                "total_file_size": file_size_str,
                "tokens_used": tokens_str,
                "total_brands": total_brands,
                "total_models": total_models,
                "total_series": total_series,
                "total_categories": total_categories
            }

        return await self.templates.TemplateResponse(
            request, 
            "dashboard/index.html",
            {
                "stats": stats,
                "brand_labels": brand_labels,
                "brand_data": brand_data,
                "brand_stats": brand_stats,
                "category_labels": cat_labels,
                "category_data": cat_data,
                "recent_activities": activity_list,
                "active_users": user_list,
                "pusher_key": settings.PUSHER_KEY or "",
                "pusher_cluster": settings.PUSHER_CLUSTER,
                "pusher_channel": settings.PUSHER_CHANNEL
            }
        )

    @expose("/api/pusher-test", methods=["POST"])
    async def pusher_test(self, request):
        """
        API to test live Pusher Realtime notifications and stats auto-update.
        """
        import random
        event_types = [
            ("new-project", "Dự án mới", f"Dự án 'Tủ Điện Trạm Biến Áp #{random.randint(100, 999)}' vừa được tạo!"),
            ("file-uploaded", "Bản vẽ tải lên", f"Tập tin 'So_Do_Nguyen_Ly_{random.randint(1, 20)}.dwg' vừa được tải lên!"),
            ("ai-completed", "Bóc tách AI hoàn tất", "Hệ thống AI vừa bóc tách thành công 48 thiết bị tủ điện!"),
            ("new-user", "Người dùng mới", f"Kỹ sư điện 'user{random.randint(10, 99)}@webbaogia.com' vừa đăng ký tài khoản!")
        ]
        ev_type, title, msg = random.choice(event_types)
        success = await pusher_service.notify_admin(
            event_type=ev_type,
            title=title,
            message=msg,
            data={"counter_increment": 1}
        )
        return JSONResponse({"status": "ok", "broadcasted": success, "type": ev_type, "title": title, "message": msg})

    @expose("/api/notifications", methods=["GET"])
    async def get_notifications(self, request):
        """
        API trả về danh sách thông báo thực tế từ database cho Admin Header Dropdown.
        """
        limit = int(request.query_params.get("limit", 15))
        async with AsyncSessionLocal() as db:
            unread_count = (await db.execute(
                select(func.count(Notification.id)).where(Notification.is_read == False)
            )).scalar() or 0

            notifs_result = await db.execute(
                select(Notification).order_by(Notification.created_at.desc()).limit(limit)
            )
            notifs = notifs_result.scalars().all()

            items = []
            now_dt = datetime.datetime.now()
            for n in notifs:
                time_ago = "Vừa xong"
                if n.created_at:
                    diff_sec = (now_dt - n.created_at).total_seconds()
                    if diff_sec < 60:
                        time_ago = "Vừa xong"
                    elif diff_sec < 3600:
                        time_ago = f"{int(diff_sec // 60)} phút trước"
                    elif diff_sec < 86400:
                        time_ago = f"{int(diff_sec // 3600)} giờ trước"
                    elif diff_sec < 86400 * 7:
                        time_ago = f"{int(diff_sec // 86400)} ngày trước"
                    else:
                        time_ago = n.created_at.strftime("%d/%m/%Y")

                items.append({
                    "id": n.id,
                    "title": n.title,
                    "body": n.body,
                    "type": n.type or "info",
                    "link": n.link or "/admin/activity-log/list",
                    "is_read": n.is_read,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                    "time_ago": time_ago
                })

            return JSONResponse({
                "unread_count": unread_count,
                "total": len(items),
                "items": items
            })

    @expose("/api/notifications/mark-read", methods=["POST"])
    async def mark_notifications_read(self, request):
        """
        API đánh dấu tất cả thông báo là đã đọc trong database.
        """
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Notification).where(Notification.is_read == False).values(is_read=True)
            )
            await db.commit()
            return JSONResponse({"status": "ok", "message": "Đã đánh dấu tất cả thông báo là đã đọc"})


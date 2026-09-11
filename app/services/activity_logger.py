import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.models.activity_log import ActivityLog
from app.models.notification import Notification
from app.models.user import User
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.conversation_session import ConversationSession
from app.services.pusher_service import pusher_service

logger = logging.getLogger(__name__)

async def get_admin_user_id(db: AsyncSession) -> int:
    """Lấy ID của quản trị viên đầu tiên để gán thông báo hệ thống nếu cần."""
    admin_user = (await db.execute(select(User.id).where(User.role == "admin").order_by(User.id.asc()).limit(1))).scalar()
    if admin_user:
        return admin_user
    first_user = (await db.execute(select(User.id).order_by(User.id.asc()).limit(1))).scalar()
    return first_user or 1

async def log_activity(
    db: AsyncSession,
    action: str,
    user_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    create_notification: bool = True,
    notification_title: Optional[str] = None,
    notification_body: Optional[str] = None,
    notification_type: str = "info",
    notification_link: Optional[str] = None,
    notify_pusher: bool = True
) -> ActivityLog:
    """
    Ghi nhận một hoạt động thực tế vào bảng activity_logs và bảng notifications,
    đồng thời phát sóng realtime tới Dashboard qua Pusher.
    """
    try:
        # 1. Tạo ActivityLog
        log_entry = ActivityLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(log_entry)

        # 2. Tạo Notification cho quản trị viên / hệ thống
        if create_notification:
            target_user_id = user_id
            if not target_user_id:
                target_user_id = await get_admin_user_id(db)

            notif = Notification(
                user_id=target_user_id,
                title=notification_title or action,
                body=notification_body or (details.get("message") if details else action),
                type=notification_type,
                link=notification_link or "/admin/activity-log/list",
                is_read=False
            )
            db.add(notif)

        await db.commit()
        await db.refresh(log_entry)

        # 3. Gửi Realtime Notification qua Pusher
        if notify_pusher:
            try:
                user_name = "Người dùng"
                if user_id:
                    u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
                    if u:
                        user_name = u.name or u.email

                await pusher_service.notify_admin(
                    event_type=notification_type,
                    title=notification_title or action,
                    message=notification_body or f"{user_name}: {action}",
                    data={
                        "action": action,
                        "user": user_name,
                        "entity_type": entity_type or "Hệ thống",
                        "link": notification_link
                    }
                )
            except Exception as pe:
                logger.warning(f"Lỗi gửi Pusher notification: {pe}")

        return log_entry
    except Exception as e:
        logger.error(f"Lỗi ghi log hoạt động: {e}")
        await db.rollback()
        raise

async def sync_initial_activities_and_notifications(db: AsyncSession):
    """
    Đồng bộ dữ liệu thực tế hiện có trong database (User, Project, ProjectFile, Session)
    vào bảng activity_logs và notifications nếu chưa có dữ liệu, đảm bảo hiển thị chuẩn 100%.
    """
    try:
        count_logs = (await db.execute(select(func.count(ActivityLog.id)))).scalar() or 0
        if count_logs > 0:
            return

        logger.info("[ActivitySync] Đang đồng bộ nhật ký hoạt động từ dữ liệu thực tế...")
        admin_id = await get_admin_user_id(db)

        # 1. Đồng bộ người dùng thật
        users = (await db.execute(select(User).order_by(User.created_at.asc()))).scalars().all()
        for u in users:
            name_display = u.name or u.email
            role_display = "Quản trị viên" if u.role == "admin" else "Kỹ sư điện"
            time_created = u.created_at or datetime.now()

            log_u = ActivityLog(
                user_id=u.id,
                action=f"Người dùng mới đăng ký: {name_display}",
                entity_type="Người dùng",
                entity_id=str(u.id),
                details={"email": u.email, "role": u.role},
                created_at=time_created
            )
            db.add(log_u)

            notif_u = Notification(
                user_id=admin_id,
                title="Người dùng mới đăng ký",
                body=f"{role_display} {name_display} vừa tham gia hệ thống",
                type="new-user",
                link="/admin/user/list",
                is_read=False,
                created_at=time_created
            )
            db.add(notif_u)

        # 2. Đồng bộ dự án thật
        projects = (await db.execute(select(Project).order_by(Project.created_at.asc()))).scalars().all()
        for p in projects:
            time_created = p.created_at or datetime.now()
            log_p = ActivityLog(
                user_id=p.user_id,
                action=f"Tạo dự án mới: '{p.name}'",
                entity_type="Dự án",
                entity_id=str(p.id),
                details={"project_name": p.name, "category": p.category or "Tủ điện"},
                created_at=time_created
            )
            db.add(log_p)

            notif_p = Notification(
                user_id=admin_id,
                title="Dự án mới được tạo",
                body=f"Dự án '{p.name}' đã được khởi tạo và sẵn sàng bóc tách",
                type="new-project",
                link="/admin/project/list",
                is_read=False,
                created_at=time_created
            )
            db.add(notif_p)

        # 3. Đồng bộ tập tin bản vẽ thật (lấy 20 tập tin gần nhất)
        files = (await db.execute(
            select(ProjectFile).order_by(ProjectFile.created_at.asc()).limit(20)
        )).scalars().all()
        for f in files:
            time_created = f.created_at or datetime.now()
            p_obj = (await db.execute(select(Project).where(Project.id == f.project_id))).scalar_one_or_none()
            p_name = p_obj.name if p_obj else f"Dự án #{f.project_id}"
            user_id = p_obj.user_id if p_obj else admin_id

            log_f = ActivityLog(
                user_id=user_id,
                action=f"Tải lên bản vẽ: {f.filename}",
                entity_type="Tập tin",
                entity_id=str(f.id),
                details={"filename": f.filename, "file_size": f.file_size, "project_name": p_name},
                created_at=time_created
            )
            db.add(log_f)

            notif_f = Notification(
                user_id=admin_id,
                title="Tập tin bản vẽ mới",
                body=f"Bản vẽ '{f.filename}' được tải lên dự án '{p_name}'",
                type="file-uploaded",
                link="/admin/project-file/list",
                is_read=False,
                created_at=time_created
            )
            db.add(notif_f)

        # 4. Đồng bộ phiên bóc tách AI
        sessions = (await db.execute(
            select(ConversationSession).order_by(ConversationSession.created_at.asc()).limit(15)
        )).scalars().all()
        for s in sessions:
            time_created = s.created_at or datetime.now()
            p_obj = (await db.execute(select(Project).where(Project.id == s.project_id))).scalar_one_or_none()
            p_name = p_obj.name if p_obj else f"Dự án #{s.project_id}"

            log_s = ActivityLog(
                user_id=s.user_id,
                action=f"Bóc tách AI hoàn tất cho dự án '{p_name}'",
                entity_type="Bóc tách AI",
                entity_id=str(s.id),
                details={"project_name": p_name, "iterations": s.total_iterations, "tokens": s.total_tokens_used},
                created_at=time_created
            )
            db.add(log_s)

            notif_s = Notification(
                user_id=admin_id,
                title="Bóc tách AI hoàn tất",
                body=f"Dự án '{p_name}' đã được phân tích hoàn tất bằng AI",
                type="ai-completed",
                link="/admin/conversation-session/list",
                is_read=False,
                created_at=time_created
            )
            db.add(notif_s)

        await db.commit()
        logger.info("[ActivitySync] Đã đồng bộ thành công nhật ký hoạt động và thông báo thực tế!")
    except Exception as e:
        logger.error(f"[ActivitySync] Lỗi đồng bộ: {e}")
        await db.rollback()

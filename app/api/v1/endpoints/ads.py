"""
Ad Gate API - Quản lý hiển thị quảng cáo cho người dùng.
Logic:
  - Lần đầu vào trang (total_downloads == 0) → bắt buộc xem quảng cáo
  - Cứ mỗi 5 file tải → hiển thị lại quảng cáo
  - Người dùng bấm "Đã xem" → mở khóa tải file
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.ad_view_log import AdViewLog
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Số file tải giữa hai lần xem quảng cáo
AD_FREQUENCY = int(getattr(settings, "AD_FREQUENCY", 5))


def ad_gate_active() -> bool:
    return bool(settings.AD_ENABLED and settings.GOOGLE_ADSENSE_CLIENT_ID
                and settings.GOOGLE_ADSENSE_SLOT_ID)


class AdCheckResponse(BaseModel):
    should_show_ad: bool
    ad_type: str           # "first_visit" | "periodic" | "none"
    downloads_since_last_ad: int
    next_ad_after: int     # còn bao nhiêu lần tải nữa thì hiện ad
    adsense_client_id: str  # Google AdSense publisher ID


class AdCompleteRequest(BaseModel):
    ad_type: str = "first_visit"


class AdCompleteResponse(BaseModel):
    success: bool
    log_id: int
    message: str


@router.get("/check", response_model=AdCheckResponse, summary="Kiểm tra có cần xem quảng cáo không")
async def check_ad_required(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AdCheckResponse:
    """
    Kiểm tra người dùng có cần xem quảng cáo trước khi tải file không.
    Gọi endpoint này TRƯỚC mỗi lần tải file.
    """
    adsense_client_id = getattr(settings, "GOOGLE_ADSENSE_CLIENT_ID", "ca-pub-0000000000000000")

    last_log_result = await db.execute(
        select(AdViewLog)
        .where(AdViewLog.user_id == current_user.id, AdViewLog.completed == True)
        .order_by(AdViewLog.id.desc()).limit(1)
    )
    last_log = last_log_result.scalar_one_or_none()
    count = last_log.download_count_after if last_log else 0
    due = last_log is None or count >= AD_FREQUENCY
    return AdCheckResponse(
        should_show_ad=due and ad_gate_active(),
        ad_type=("first_visit" if last_log is None else "periodic") if due else "none",
        downloads_since_last_ad=count,
        next_ad_after=0 if due else AD_FREQUENCY - count,
        adsense_client_id=adsense_client_id,
    )


@router.post("/complete", response_model=AdCompleteResponse, summary="Xác nhận đã xem quảng cáo")
async def complete_ad_view(
    body: AdCompleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AdCompleteResponse:
    """
    Gọi endpoint này khi người dùng bấm 'Đã xem' / bỏ qua quảng cáo.
    Tạo log mới, reset download_count_after = 0 để bắt đầu đếm lại.
    """
    previous_result = await db.execute(
        select(AdViewLog).where(AdViewLog.user_id == current_user.id,
                                AdViewLog.completed == True)
        .order_by(AdViewLog.id.desc()).limit(1)
    )
    previous = previous_result.scalar_one_or_none()
    if previous and previous.download_count_after < AD_FREQUENCY:
        raise HTTPException(status_code=409, detail="Chưa đến lượt xem quảng cáo.")
    total_now = (previous.total_downloads_at_view + previous.download_count_after) if previous else 0

    log = AdViewLog(
        user_id=current_user.id,
        download_count_after=0,
        total_downloads_at_view=total_now,
        ad_type=body.ad_type,
        completed=True,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)

    return AdCompleteResponse(
        success=True,
        log_id=log.id,
        message=f"Đã ghi nhận xem quảng cáo. Bạn có thể tải {AD_FREQUENCY} file tiếp theo.",
    )


@router.post("/track-download", summary="Ghi nhận 1 lần tải file")
async def track_download(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """
    Gọi endpoint này mỗi khi người dùng tải thành công 1 file.
    Tăng download_count_after trong log hiện tại.
    """
    # Lấy log gần nhất chưa đủ AD_FREQUENCY
    last_log_result = await db.execute(
        select(AdViewLog)
        .where(AdViewLog.user_id == current_user.id)
        .where(AdViewLog.completed == True)
        .order_by(AdViewLog.id.desc())
        .limit(1)
    )
    last_log = last_log_result.scalar_one_or_none()

    if ad_gate_active() and (last_log is None or last_log.download_count_after >= AD_FREQUENCY):
        raise HTTPException(status_code=403, detail="Cần xem quảng cáo trước khi tải file.")
    if last_log:
        last_log.download_count_after += 1
        await db.commit()
        downloads_after = last_log.download_count_after
    else:
        # Ads are disabled; no ad log is needed, but downloads stay available.
        downloads_after = 0

    next_ad_in = max(0, AD_FREQUENCY - downloads_after)
    return {
        "success": True,
        "downloads_since_last_ad": downloads_after,
        "next_ad_after": next_ad_in,
        "ad_threshold": AD_FREQUENCY,
    }


@router.get("/config", summary="Lấy cấu hình quảng cáo (public)")
async def get_ad_config() -> dict:
    """Trả về cấu hình AdSense và tần suất quảng cáo (không cần auth)."""
    return {
        "adsense_client_id": getattr(settings, "GOOGLE_ADSENSE_CLIENT_ID", ""),
        "adsense_slot_id": getattr(settings, "GOOGLE_ADSENSE_SLOT_ID", ""),
        "ad_frequency": AD_FREQUENCY,
        "ad_enabled": ad_gate_active(),
    }

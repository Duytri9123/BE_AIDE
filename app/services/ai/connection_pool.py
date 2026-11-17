"""
Connection Pool Service
Quản lý xoay vòng (round-robin) các AiConnection theo thứ tự ưu tiên.
Khi connection chính bị lỗi (429, 401, timeout, 503), tự động chuyển sang connection tiếp theo.
"""
import logging
import asyncio
import re
from typing import List, Tuple, Callable, Any, Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.ai_connection import AiConnection
from app.models.ai_provider import AiProvider
from app.models.ai_provider_model import AiProviderModel
from app.core.exceptions import (
    AIVisionError,
    AITimeoutError,
    AIRateLimitError,
    AIAuthenticationError,
    ImageParsingError,
)
from app.services.ai.token_refresh_service import TokenRefreshService
from app.services.ai.el_progress import run_step

logger = logging.getLogger(__name__)

# Các exception cho phép fallback sang connection tiếp theo
RETRYABLE_EXCEPTIONS = (
    AIRateLimitError,      # 429
    AIAuthenticationError, # 401
    AITimeoutError,        # timeout
)

# Các exception KHÔNG cho phép fallback (lỗi business logic)
NON_RETRYABLE_EXCEPTIONS = (
    ImageParsingError,     # file không tồn tại / không đọc được
)



def _get_db_lock(db: AsyncSession) -> asyncio.Lock:
    lock = getattr(db, "_aide_db_lock", None)
    if lock is None:
        lock = asyncio.Lock()
        setattr(db, "_aide_db_lock", lock)
    return lock

class ConnectionPoolService:
    """Service quản lý connection pool với round-robin fallback."""

    @staticmethod
    async def get_top_model_for_provider(db: AsyncSession, provider: str) -> Optional[str]:
        """Lấy model có thứ tự ưu tiên cao nhất (#1) từ danh mục AiProviderModel cho provider này."""
        try:
            stmt = (
                select(AiProviderModel.model_key)
                .join(AiProvider, AiProvider.id == AiProviderModel.provider_id)
                .where(
                    AiProviderModel.provider_id == provider.lower(),
                    AiProviderModel.is_active.is_(True),
                    AiProvider.is_active.is_(True),
                )
                .order_by(AiProviderModel.sort_order.asc(), AiProviderModel.id.asc())
                .limit(1)
            )
            async with _get_db_lock(db):
                res = await db.execute(stmt)
            return res.scalar_one_or_none()
        except Exception as ex:
            logger.warning(f"Không thể lấy model ưu tiên cho provider {provider}: {ex}")
            return None

    @staticmethod
    async def get_ordered_models_for_provider(db: AsyncSession, provider: str) -> List[str]:
        """Lấy danh sách các model đang hoạt động theo thứ tự ưu tiên (sort_order ASC, id ASC) của provider."""
        try:
            stmt = (
                select(AiProviderModel.model_key)
                .join(AiProvider, AiProvider.id == AiProviderModel.provider_id)
                .where(
                    AiProviderModel.provider_id == provider.lower(),
                    AiProviderModel.is_active.is_(True),
                    AiProvider.is_active.is_(True),
                )
                .order_by(AiProviderModel.sort_order.asc(), AiProviderModel.id.asc())
            )
            async with _get_db_lock(db):
                res = await db.execute(stmt)
            return list(res.scalars().all())
        except Exception as ex:
            logger.warning(f"Không thể lấy danh mục model cho provider {provider}: {ex}")
            return []

    @staticmethod
    async def get_ordered_connections(db: AsyncSession) -> List[AiConnection]:
        """
        Lấy các AiConnection active của provider đang hoạt động, sắp theo priority
        ASC (nhỏ = ưu tiên cao), created_at DESC. Chỉ lấy connection có api_key
        hợp lệ để tránh FE gọi sang provider đã bị tắt trong trang quản trị.
        """
        stmt = (
            select(AiConnection)
            .join(AiProvider, AiProvider.id == AiConnection.provider)
            .where(
                AiProvider.is_active.is_(True),
                AiConnection.is_active == True,
                AiConnection.api_key.isnot(None),
                AiConnection.api_key != "",
                AiConnection.selected_model.isnot(None),
                AiConnection.selected_model != "",
                AiConnection.status != "rate_limited",
                AiConnection.status != "inactive",
            )
            .order_by(AiConnection.priority.asc(), AiConnection.created_at.desc())
        )
        async with _get_db_lock(db):
            result = await db.execute(stmt)
        connections = result.scalars().all()
        return list(connections)

    @staticmethod
    async def _record_connection_error(
        db: AsyncSession, connection: AiConnection, error_msg: str
    ):
        """Ghi nhận lỗi vào connection để admin theo dõi sức khoẻ pool."""
        try:
            async with _get_db_lock(db):
                await db.execute(
                    update(AiConnection)
                    .where(AiConnection.id == connection.id)
                    .values(
                        last_error_at=datetime.now(timezone.utc),
                        last_error_message=str(error_msg)[:1000],
                    )
                )
                await db.commit()
        except Exception as e:
            logger.warning(f"Không thể cập nhật lỗi cho connection {connection.name}: {e}")

    @staticmethod
    async def call_with_fallback(
        db: AsyncSession,
        connections: List[AiConnection],
        call_fn: Callable,
        **call_kwargs: Any,
    ) -> Tuple[str, AiConnection]:
        """Retry accounts using the configured model; never downgrade to another model."""
        if not connections:
            raise AIVisionError(
                "Không có kết nối AI nào khả dụng. Vui lòng cấu hình ít nhất 1 kết nối AI trong Admin.",
                {"hint": "no_active_connections"}
            )

        configured_model = (connections[0].selected_model or '').strip()
        if not configured_model:
            raise AIVisionError('Chưa chọn model cho kết nối AI.', {'hint': 'missing_selected_model'})
        # Connection failover is allowed only when it retains this exact model.
        connections = [c for c in connections if (c.selected_model or '').strip() == configured_model]
        # The caller must not override the model selected for a BE connection.
        call_kwargs.pop("model", None)
        last_error: Optional[Exception] = None
        errors_log: List[str] = []

        provider_connections: dict[str, List[AiConnection]] = {}
        provider_order: List[str] = []
        for conn in connections:
            provider = conn.provider.lower()
            if provider not in provider_connections:
                provider_connections[provider] = []
                provider_order.append(provider)
            provider_connections[provider].append(conn)

        # Lấy thông tin metadata các provider (base_url, api_type) để truyền cho các provider OpenAI-compatible
        prov_map: dict[str, AiProvider] = {}
        try:
            p_stmt = select(AiProvider).where(AiProvider.id.in_(provider_order))
            async with _get_db_lock(db):
                p_res = await db.execute(p_stmt)
            prov_map = {p.id.lower(): p for p in p_res.scalars().all()}
        except Exception as pe:
            logger.warning("ConnectionPool: Không thể load metadata provider: %s", pe)

        for provider in provider_order:
            provider_accounts = provider_connections[provider]
            prov_obj = prov_map.get(provider)
            provider_base_url = prov_obj.base_url if prov_obj else None

            candidate_models = [configured_model]
            base_model = re.sub(r"-(?:high|medium|low)$|-tiered\([a-z]+\)$", "", configured_model)
            if base_model and base_model != configured_model and base_model not in candidate_models:
                candidate_models.append(base_model)

            disabled_account_ids: set[int] = set()
            failed_base_models: set[str] = set()
            for model_idx, model_to_use in enumerate(candidate_models):
                # Rút ngắn thời gian chờ: nếu model gốc của biến thể này đã thất bại trên toàn bộ tài khoản
                # thì bỏ qua các biến thể tiered tiếp theo (ví dụ: gemini-3.6-flash đã timeout ở high thì bỏ qua medium & low)
                raw_base = (model_to_use or "").removeprefix("ag/").removeprefix("models/")
                for sfx in ["-tiered(high)", "-tiered(medium)", "-tiered(low)", "-high", "-medium", "-low"]:
                    raw_base = raw_base.replace(sfx, "")
                raw_base = raw_base.strip().lower()

                if raw_base in failed_base_models:
                    logger.info(
                        "ConnectionPool: Bỏ qua biến thể '%s' vì model gốc '%s' đã thất bại trên toàn bộ tài khoản.",
                        model_to_use, raw_base
                    )
                    continue

                attempted_accounts = 0
                for provider_conn_idx, conn in enumerate(provider_accounts):
                    if conn.id in disabled_account_ids:
                        continue
                    attempted_accounts += 1
                    conn_label = (
                        f"[{provider_conn_idx+1}/{len(provider_accounts)}] {conn.name} "
                        f"({provider}/{model_to_use}, Priority={conn.priority})"
                    )
                    max_attempts = 2
                    for attempt in range(1, max_attempts + 1):
                        try:
                            logger.info("ConnectionPool: Đang thử %s (Lần thử %s/%s)", conn_label, attempt, max_attempts)
                            call_args = dict(call_kwargs)
                            conn_base_url = (conn.quotas or {}).get("base_url") if isinstance(conn.quotas, dict) else None
                            eff_base_url = conn_base_url or provider_base_url
                            if eff_base_url and "base_url" not in call_args:
                                call_args["base_url"] = eff_base_url
                            
                            active_api_key = await TokenRefreshService.get_active_token(conn.api_key)
                            result = await run_step("Đang chờ phản hồi model", call_fn(
                                provider=provider,
                                api_key=active_api_key,
                                model=model_to_use,
                                **call_args,
                            ), detail=f"{model_to_use} · Lần gọi {attempt}")
                            logger.info("ConnectionPool: Thành công với %s", conn_label)
                            setattr(conn, "actual_model", model_to_use)
                            return result, conn

                        except NON_RETRYABLE_EXCEPTIONS:
                            logger.exception("ConnectionPool: Lỗi không thể retry tại %s", conn_label)
                            raise

                        except AIAuthenticationError as e:
                            error_msg = f"AIAuthenticationError: {e}"
                            errors_log.append(f"{conn_label} -> {error_msg}")
                            last_error = e
                            disabled_account_ids.add(conn.id)
                            await ConnectionPoolService._record_connection_error(db, conn, error_msg)
                            logger.warning(
                                "ConnectionPool: %s lỗi xác thực: %s; đổi sang tài khoản khác cùng model.",
                                conn_label,
                                error_msg
                            )
                            break

                        except Exception as e:
                            err_str = str(e).lower()
                            is_503 = "503" in err_str or "temporarily unavailable" in err_str or "high demand" in err_str
                            is_404_model = "404" in err_str or "không tồn tại" in err_str or "no longer available" in err_str
                            is_retryable = isinstance(e, RETRYABLE_EXCEPTIONS) or (
                                isinstance(e, AIVisionError) and (is_503 or is_404_model)
                            )
                            if not is_retryable:
                                logger.exception("ConnectionPool: Lỗi không thể retry tại %s", conn_label)
                                raise
                            if is_503 and attempt < max_attempts:
                                logger.warning("ConnectionPool: %s gặp 503 High Demand, chờ 1.5s thử lại lần %s...", conn_label, attempt + 1)
                                await asyncio.sleep(1.5)
                                continue
                            error_msg = f"{type(e).__name__}: {e}"
                            errors_log.append(f"{conn_label} -> {error_msg}")
                            last_error = e
                            await ConnectionPoolService._record_connection_error(db, conn, error_msg)
                            logger.warning(
                                "ConnectionPool: %s thất bại do: %s; đổi sang tài khoản khác cùng model trước.",
                                conn_label,
                                error_msg
                            )
                            break

                if attempted_accounts:
                    is_tier_capacity = "CAPACITY" in str(last_error or "").upper() or "503" in str(last_error or "")
                    if not is_tier_capacity:
                        failed_base_models.add(raw_base)
                    if model_idx + 1 < len(candidate_models):
                        next_model = candidate_models[model_idx + 1]
                        logger.warning(
                            "ConnectionPool: tất cả tài khoản %s đã lỗi với model '%s'; chuyển sang model '%s'.",
                            provider, model_to_use, next_model,
                        )

        # Toàn bộ connections và candidate models đều thất bại
        formatted_chain = "\n".join(f"  • {err}" for err in errors_log)
        logger.error(f"ConnectionPool: Tất cả {len(connections)} connections đều thất bại:\n{formatted_chain}")

        last_err_str = str(last_error or "")
        last_err_upper = last_err_str.upper()
        if "503" in last_err_str or "MODEL_CAPACITY_EXHAUSTED" in last_err_upper or "CAPACITY" in last_err_upper or "UNAVAILABLE" in last_err_upper:
            user_msg = "Máy chủ AI hiện đang quá tải hoặc tạm thời hết công suất phục vụ. Bạn vui lòng thử lại sau giây lát."
        elif "429" in last_err_str or "RESOURCE_EXHAUSTED" in last_err_upper or "RATE" in last_err_upper:
            user_msg = "Hệ thống AI đang tiếp nhận nhiều yêu cầu cùng lúc. Bạn vui lòng đợi ít giây rồi thử lại."
        elif "401" in last_err_str or "AUTH" in last_err_upper:
            user_msg = "Kết nối máy chủ AI tạm thời bị gián đoạn xác thực. Vui lòng thử lại sau."
        elif "timeout" in last_err_str.lower():
            user_msg = "Thời gian phản hồi từ máy chủ AI bị quá hạn. Bạn vui lòng thử lại."
        else:
            user_msg = "Hệ thống máy chủ AI tạm thời gián đoạn kết nối. Bạn vui lòng thử lại sau giây lát."

        raise AIVisionError(
            user_msg,
            {
                "total_connections": len(connections),
                "errors": errors_log,
                "last_error": str(last_error),
            }
        )

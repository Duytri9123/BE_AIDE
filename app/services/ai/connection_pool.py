"""
Connection Pool Service
Quản lý xoay vòng (round-robin) các AiConnection theo thứ tự ưu tiên.
Khi connection chính bị lỗi (429, 401, timeout, 503), tự động chuyển sang connection tiếp theo.
"""
import logging
import asyncio
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
        result = await db.execute(stmt)
        connections = result.scalars().all()
        return list(connections)

    @staticmethod
    async def _record_connection_error(
        db: AsyncSession, connection: AiConnection, error_msg: str
    ):
        """Ghi nhận lỗi vào connection để admin theo dõi sức khoẻ pool."""
        try:
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
        """
        Thực thi gọi AI với cơ chế xoay vòng đa tầng (Connection Pool & Model Fallback Cascade):
        1. Xoay vòng theo thứ tự ưu tiên của Tài khoản (AiConnection: Priority 1 -> 2 -> ...).
        2. Với mỗi tài khoản, gọi theo danh sách model ưu tiên đang hoạt động
           của chính provider đó.
        3. Nếu model gặp lỗi retryable (HTTP 503 Quá tải, HTTP 429 Quota, 404 Model), tự động fallback
           sang các Model ưu tiên tiếp theo trong bảng AiProviderModel (#2, #3, ...) của chính tài khoản đó.
        4. Nếu toàn bộ model của tài khoản đó đều thất bại, tự động chuyển sang Tài khoản tiếp theo theo Priority.
        5. Ghi nhận nhật ký xoay vòng minh bạch và chi tiết.
        """
        if not connections:
            raise AIVisionError(
                "Không có kết nối AI nào khả dụng. Vui lòng cấu hình ít nhất 1 kết nối AI trong Admin.",
                {"hint": "no_active_connections"}
            )

        # The caller must not override the model selected for a BE connection.
        call_kwargs.pop("model", None)
        last_error: Optional[Exception] = None
        errors_log: List[str] = []

        # Account-first fallback: try every account of one provider with the
        # same highest-priority model before lowering that model.  This avoids
        # downgrading a request merely because one account is temporarily busy.
        provider_connections: dict[str, List[AiConnection]] = {}
        provider_order: List[str] = []
        for conn in connections:
            provider = conn.provider.lower()
            if provider not in provider_connections:
                provider_connections[provider] = []
                provider_order.append(provider)
            provider_connections[provider].append(conn)

        for provider in provider_order:
            provider_accounts = provider_connections[provider]
            candidate_models = await ConnectionPoolService.get_ordered_models_for_provider(db, provider)
            if not candidate_models:
                logger.warning("ConnectionPool: bỏ qua provider %s vì không có model đang hoạt động.", provider)
                continue

            disabled_account_ids: set[int] = set()
            for model_idx, model_to_use in enumerate(candidate_models):
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
                            result = await call_fn(
                                provider=provider,
                                api_key=conn.api_key,
                                model=model_to_use,
                                **call_kwargs,
                            )
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

                if attempted_accounts and model_idx + 1 < len(candidate_models):
                    next_model = candidate_models[model_idx + 1]
                    logger.warning(
                        "ConnectionPool: tất cả tài khoản %s đã lỗi với model '%s'; mới hạ xuống model '%s'.",
                        provider, model_to_use, next_model,
                    )

        # Toàn bộ connections và candidate models đều thất bại
        formatted_chain = "\n".join(f"  • {err}" for err in errors_log)
        logger.error(f"ConnectionPool: Tất cả {len(connections)} connections đều thất bại:\n{formatted_chain}")

        raise AIVisionError(
            f"Tất cả {len(connections)} kết nối AI đều thất bại sau các lượt thử xoay vòng.\n"
            f"Chi tiết lịch sử thử nghiệm:\n{formatted_chain}\n\n"
            f"Lỗi cuối cùng: {str(last_error)}. Vui lòng kiểm tra lại trạng thái API Key hoặc cấu hình Model trong Admin.",
            {
                "total_connections": len(connections),
                "errors": errors_log,
                "last_error": str(last_error),
            }
        )

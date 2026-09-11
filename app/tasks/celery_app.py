from celery import Celery
import os
from app.core.config import settings

CELERY_BROKER_URL = getattr(settings, "CELERY_BROKER_URL", os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0"))
CELERY_RESULT_BACKEND = getattr(settings, "CELERY_RESULT_BACKEND", os.getenv("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/1"))

celery_app = Celery(
    "aide_worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.tasks.worker_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
    task_track_started=True,
    result_expires=86400,  # Lưu kết quả task trong Redis 24 giờ
    worker_prefetch_multiplier=1,  # Phù hợp cho task xử lý bản vẽ nặng
    broker_connection_retry_on_startup=True,
)

"""Local cold-run switch. Default behavior disables AI cache to ensure fresh takeoff without stale data."""
import os


def ai_cache_enabled():
    # Mặc định tắt cache AI (0) để đảm bảo mọi lượt bóc tách mới luôn phân tích tươi mới trực tiếp từ bản vẽ,
    # không sử dụng lại kết quả cũ gây sai lệch.
    return os.environ.get('ELQUOTE_AI_CACHE_ENABLED', '0').strip().lower() in {'1', 'true', 'on'}


def takeoff_concurrency():
    try:return max(3,min(8,int(os.environ.get('ELQUOTE_TAKEOFF_CONCURRENCY','3'))))
    except ValueError:return 3

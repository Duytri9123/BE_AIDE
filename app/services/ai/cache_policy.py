"""Local cold-run switch. Default behavior keeps the normal AI cache enabled."""
import os


def ai_cache_enabled():
    return os.environ.get('ELQUOTE_AI_CACHE_ENABLED', '1').strip().lower() not in {'0', 'false', 'off'}


def takeoff_concurrency():
    try:return max(1,min(8,int(os.environ.get('ELQUOTE_TAKEOFF_CONCURRENCY','2'))))
    except ValueError:return 2

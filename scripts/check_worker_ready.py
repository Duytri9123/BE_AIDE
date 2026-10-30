"""Check the same Redis heartbeat used by queue admission; no AI calls."""
import os
import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_root))
os.chdir(backend_root)

from app.services import job_queue


def main():
    try:
        with job_queue.sync_client() as client:
            ready = bool(client.exists(job_queue.READY_KEY))
        print('READY' if ready else 'NOT_READY')
        return 0 if ready else 1
    except Exception:
        print('UNAVAILABLE')
        return 2


if __name__ == '__main__':
    sys.exit(main())

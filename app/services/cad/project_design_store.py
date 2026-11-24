"""Atomic JSON storage with a cross-process revision lock for Uvicorn workers."""
import json
import os
import time
from contextlib import contextmanager
from uuid import uuid4


@contextmanager
def _locked(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix('.lock').open('a+b') as stream:
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            until = time.monotonic()+5
            while True:
                try:
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() >= until:
                        raise TimeoutError('Thiết kế đang được lưu ở cửa sổ khác.')
                    time.sleep(.025)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def save_designs(path, designs, revision, *, owner_id=0, actor_id=0):
    with _locked(path):
        from .design_learning import save_snapshot
        return save_snapshot(path, designs, revision, owner_id=owner_id, actor_id=actor_id)

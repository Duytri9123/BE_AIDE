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


def save_designs(path, designs, revision):
    with _locked(path):
        previous = json.loads(path.read_text(encoding='utf8')) if path.is_file() else {'revision': ''}
        if revision != previous.get('revision', ''):
            raise ValueError('Thiết kế đã đổi ở cửa sổ khác. Tải lại trước khi lưu.')
        result = {'schema_version': 1, 'revision': uuid4().hex, 'designs': designs}
        content = json.dumps(result, ensure_ascii=False, allow_nan=False)
        if len(content.encode('utf8')) > 20_000_000:
            raise OverflowError('Dữ liệu thiết kế vượt 20 MB.')
        temporary = path.with_suffix('.'+uuid4().hex+'.tmp')
        temporary.write_text(content, encoding='utf8')
        temporary.replace(path)
        return {'revision': result['revision']}

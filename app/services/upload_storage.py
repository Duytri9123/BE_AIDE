"""Bounded upload writes with atomic publication after successful completion."""
import os
import uuid
from pathlib import Path
import aiofiles
from fastapi import HTTPException


async def save_upload(file, directory: Path, max_bytes: int):
    name = file.filename or ''
    if not name or name in ('.', '..') or '/' in name or '\\' in name or ':' in name:
        raise HTTPException(400, 'Tên file không hợp lệ')
    if file.size is not None and file.size > max_bytes:
        raise HTTPException(413, 'File vượt quá kích thước cho phép')
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / name
    pending = directory / ('.upload-' + uuid.uuid4().hex + '.tmp')
    total = 0
    try:
        async with aiofiles.open(pending, 'wb') as output:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(413, 'File vượt quá kích thước cho phép')
                await output.write(chunk)
        os.replace(pending, target)
        return target, total
    finally:
        pending.unlink(missing_ok=True)

"""Versioned, price-free catalog information shipped with application code.

CAD geometry remains in the managed CatalogTB installation. This overlay only
updates information tables and reviewed library classification, never ratings
on the source CAD or permission to insert a drawing.
"""
import json
from functools import lru_cache
from pathlib import Path

INFORMATION_PATH=Path(__file__).resolve().parents[1]/'data/catalogtb_published_information.json'


@lru_cache(maxsize=2)
def _load(path, revision):
    return json.loads(Path(path).read_text(encoding='utf8')).get('profiles',{})


def published_information():
    if not INFORMATION_PATH.is_file():
        return {}
    stat=INFORMATION_PATH.stat()
    return _load(str(INFORMATION_PATH), (stat.st_mtime_ns,stat.st_size))


def apply_published_information(profile, relative, information=None):
    row=(published_information() if information is None else information).get(relative)
    if not row:
        return profile
    allowed={'catalog_tham_khao','nhom_thu_vien','ten_san_pham','ma_dong_san_pham','catalog_information_type'}
    return {**profile,**{key:value for key,value in row.items() if key in allowed}}

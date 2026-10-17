"""Public, separately labelled product references from other manufacturers."""
import json
from pathlib import Path
from functools import lru_cache

PATH=Path(__file__).resolve().parents[1]/'data/published_other_manufacturers.json'

@lru_cache(maxsize=2)
def _load(revision):
    return json.loads(PATH.read_text(encoding='utf8')).get('profiles',{})

def other_manufacturer_options(device):
    if not PATH.is_file():return []
    stat=PATH.stat();registry=_load((stat.st_mtime_ns,stat.st_size))
    result=[]
    for identity in dict.fromkeys([device.get('id'),*(device.get('member_profile_ids') or [])]):
        result.extend(registry.get(identity,[]))
    return result

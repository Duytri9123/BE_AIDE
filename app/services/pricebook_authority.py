"""Honor user-selected exclusive manufacturer pricebooks across public readers."""
import json
from functools import lru_cache
from pathlib import Path
from .ai.manufacturer_registry import canonical_brand

PATH=Path(__file__).resolve().parents[1]/'data/pricebook_authorities.json'

@lru_cache(maxsize=2)
def _policies(revision):
 data=json.loads(PATH.read_text(encoding='utf8'))
 return {canonical_brand(brand):{**rule,'row_ids':set(rule.get('row_ids',[]))}
         for brand,rule in data.get('manufacturers',{}).items() if rule.get('exclusive') is True}

def _current_policies():
 if not PATH.is_file():return {}
 stat=PATH.stat();return _policies((stat.st_mtime_ns,stat.st_size))

def _allowed(row,policies):
 rule=policies.get(canonical_brand(row.get('brand')))
 if not rule:return True
 return (row.get('id') in rule['row_ids'] and row.get('source_kind')=='supplier_pricebook'
         and row.get('source_url')==rule['source_url'] and row.get('source_sha256')==rule['source_sha256'])

def published_row_allowed(row):
 return _allowed(row,_current_policies())

def filter_published_rows(rows):
 # Read the policy revision once for an entire catalog, not once per row.
 policies=_current_policies()
 return [r for r in rows if _allowed(r,policies)]

def publish_authority(brand,rows,source_sha256,effective_date):
 assert rows and all(r.get('source_sha256')==source_sha256 and canonical_brand(r.get('brand'))==canonical_brand(brand) for r in rows)
 data=json.loads(PATH.read_text(encoding='utf8')) if PATH.exists() else {'schema_version':1,'manufacturers':{}}
 data['manufacturers'][canonical_brand(brand)]={'exclusive':True,'source_sha256':source_sha256,
  'source_url':rows[0]['source_url'],'effective_date':effective_date,'row_ids':[r['id'] for r in rows],
  'reason':'User selected this PDF as the exclusive published pricebook for this manufacturer.'}
 pending=PATH.with_suffix('.json.tmp');pending.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8');pending.replace(PATH)

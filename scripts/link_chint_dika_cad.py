"""Publish reviewed CAD browsing links for the existing DIKA June-2026 book.

These are family/configuration browsing links, not exact SKU insertion approval.
The allowlist excludes unknown poles, unresolved timer/head variants, absent
NM8N models and NXR ranges outside the native body. Reviewed NXC geometry may
span coil-voltage variants; it never transfers their electrical ratings.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.price_row_cad_detail import row_configuration_digest
from app.services.catalog_product_sections import device_poles

SOURCE_SHA = 'd40237b3c908363ec273e91849b59f3b069ea644f3c79214cf6091773fd07def'
# Pole identities already reviewed in the CatalogTB source-label registry.
SOURCE_POLES = {'SRC_CHINT_461e4acca29b':'1P', 'SRC_CHINT_32fc1ea2167e':'2P',
 'SRC_CHINT_86e3bb0dcf16':'3P', 'SRC_CHINT_54593f3909d0':'3P'}
# Exact published row IDs reviewed against the existing identified CAD profiles.
REVIEW = {
 'SRC_CHINT_461e4acca29b': [('2:0', r, 4) for r in range(3, 8)],
 'SRC_CHINT_32fc1ea2167e': [('2:0', r, 5) for r in range(3, 8)],
 'SRC_CHINT_86e3bb0dcf16': [('2:0', r, 6) for r in range(3, 8)],
 'OFFICIAL-NXC-06-16-3P': [('4:0', r, 15) for r in (5, 6, 7)],
 'OFFICIAL-NXC-18-22-3P': [('4:0', r, 15) for r in (8, 9)],
 'OFFICIAL-NXC-25-38-3P': [('4:0', r, 15) for r in (10, 11, 12)],
 'OFFICIAL-NXC-40-3P': [('4:0', 13, 15)],
 'OFFICIAL-NXC-75-100-3P': [('4:0', r, 15) for r in (16, 17, 18)],
 'OFFICIAL-NXC-225-3P': [('4:0', 22, 15)],
 'OFFICIAL-NXR-38-3P': [('5:0', 3, 6)],
 'OFFICIAL-NXR-100-3P': [('5:0', r, 6) for r in (4, 5, 6)],
 'OFFICIAL-NXR-630-125-400A-3P': [('5:0', 8, 6)],
 'OFFICIAL-STEP-NXM-250S-3P': [('3:0', 5, 5)],
 'SRC_CHINT_54593f3909d0': [('3:0', 11, 5)],
 'XJ3_G': [('7:1', 2, 6)],
}
# The user accepts reviewed geometry compatibility across electrical/nameplate
# variants. CHINT's NXC dimensional families do not change with 220/380VAC coils.
for folder,cells in REVIEW.items():
 if folder.startswith('OFFICIAL-NXC-') and folder!='OFFICIAL-NXC-400-3P':
  cells.extend((table,line,18) for table,line,column in list(cells) if column==15)


def main():
 rows = {r['id']: r for r in json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items']}
 updates = []
 for folder, cells in REVIEW.items():
  path = ROOT/'data/CatalogTB/Chint/ThietBi'/folder/'thong_tin_thiet_bi.json'
  profile = json.loads(path.read_text(encoding='utf8'))
  # Source-label identities are hash reviewed by the browser, not guessed here.
  from app.services.catalog_source_identification import apply_source_identification
  device = {'brand':'CHINT','product_code':profile.get('ma_dong_san_pham'), 'spec':profile.get('thong_so',{})}
  apply_source_identification(device, profile, path, ROOT/'data/CatalogTB')
  if folder in SOURCE_POLES:device['spec']={**device['spec'],'so_cuc':SOURCE_POLES[folder]}
  assert device.get('product_code'), folder
  refs = copy.deepcopy(profile.get('catalog_tham_khao') or {})
  options = [o for o in refs.get('options',[]) if o.get('basis')!='reviewed_chint_dika_cad']
  for table, line, column in cells:
   row = rows[f'chint-dika-2026-06:{table}:{line}:{column}']
   assert row['brand']=='CHINT' and row['source_sha256']==SOURCE_SHA
   options.append({'brand':'CHINT','model':row['sku'],'source_row_id':row['id'],
    'specifications':row['specifications'],'source_url':row['source_url'],'source_page':row['source_page'],
    'basis':'reviewed_chint_dika_cad','exact_cad_match':False,
    'source_row_configuration_sha256':row_configuration_digest(row),
    'reviewed_device_model':device['product_code'],'reviewed_device_poles':device_poles(device),
    'geometry_compatibility_review':{'basis':'Named NXC frame and pole count share manufacturer dimensional drawings across coil ratings' if folder.startswith('OFFICIAL-NXC-') else 'Reviewed model and pole configuration',
      'electrical_equivalence':False,'user_accepts_compatible_geometry':True}})
  refs.update(options=options,row_links_reviewed=True)
  profile['catalog_tham_khao']=refs
  profile['chint_dika_cad_review']={'checked_at':'2026-11-05','source_sha256':SOURCE_SHA,
   'scope':'Identified model and pole configuration; NXC geometry shared across 220/380VAC coils; NXR-630 125–400A only. CAD browsing, not exact SKU approval.'}
  updates.append((path,profile))
 # Validate all references before writing any profile.
 for path,profile in updates:
  path.write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 # Keep the shipped information overlay consistent with the managed profiles.
 overlay_path=ROOT/'app/data/catalogtb_published_information.json'
 overlay=json.loads(overlay_path.read_text(encoding='utf8'))
 references={}
 for path,profile in updates:
  key='TB-'+hashlib.sha1(path.relative_to(ROOT/'data/CatalogTB').as_posix().encode()).hexdigest()[:16]
  overlay['profiles'].setdefault(key,{})['catalog_tham_khao']=profile['catalog_tham_khao']
  references[key]=profile['catalog_tham_khao']
 overlay_path.write_text(json.dumps(overlay,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 # This is a metadata-only update: preserve the already validated view inventory.
 snapshot_path=ROOT/'data/CatalogTB/_agent_index/browser_display_v5.json'
 if snapshot_path.is_file():
  snapshot=json.loads(snapshot_path.read_text(encoding='utf8'))
  for device in snapshot['items']:
   if device['id'] in references:device['catalog_references']=references[device['id']]
  pending=snapshot_path.with_suffix('.tmp')
  pending.write_text(json.dumps(snapshot,ensure_ascii=False),encoding='utf8')
  pending.replace(snapshot_path)
 print(json.dumps({'profiles':len(updates),'row_links':sum(len(v) for v in REVIEW.values())}))


if __name__=='__main__':main()

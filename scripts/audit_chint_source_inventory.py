"""Track discovered official CAD links separately from imported, validated geometry."""
import json,csv,collections
from urllib.parse import unquote,urlparse
from ls_native_writer import ROOT,CAT

def main():
 out=ROOT/'docs/chint-research-2026-10-21';out.mkdir(exist_ok=True)
 published=json.loads((ROOT/'docs/chint-full-faces-2026-10-21.json').read_text())
 reviewed={r['family'].removeprefix('STEP-') for r in published}
 reviewed_hashes={r.get('step_sha256') for r in published}
 downloaded={}
 for p in (CAT/'Chint/NguonBenNgoai').glob('*/source.json'):
  d=json.loads(p.read_text());url=d.get('source_url','');downloaded[unquote(url)]=(p.parent.name,d.get('sha256') or d.get('step_sha256'))
 records=[]
 for line in ['nxm','nm8n']:
  page='https://www.chintglobal.com/global/en/products/low-voltage/iec/secondary-power-distribution/'+line+'.html'
  for url in json.loads((ROOT/'tmp/chint-research-2026-10-21'/(line+'-cad-links.json')).read_text()):
   found=downloaded.get(unquote(url));ident=found[0] if found else None
   imported=ident in reviewed or bool(found and found[1] in reviewed_hashes)
   records.append({'line':line.upper(),'file':unquote(urlparse(url).path.rsplit('/',1)[-1]),'url':url,'manufacturer_page':page,'local_source':ident,'status':'six_views_imported_reference_only' if imported else 'downloaded_pending_review' if found else 'discovered_not_downloaded','note':('Dimensions and source assembly configuration require review; no price link published.' if found and not imported else '')})
 (out/'official-cad-inventory.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
 with (out/'official-cad-inventory.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
 summary={'links_discovered':len(records),'by_line':dict(collections.Counter(r['line'] for r in records)),'by_status':dict(collections.Counter(r['status'] for r in records)),'reviewed_families':sorted(reviewed),'reviewed_faces':24,'linked_price_rows':7,'not_complete':True,'review_pending':{'NXM-125S-2P/3P/4P':'STEP contains projecting solid components; H=231.2 vs catalogue body H=135 mm. Do not trim unidentified manufacturer parts or assign as an approved body.','NXM-250S-2P':'Source contains loose components and an inner 320-labelled assembly. Requires manufacturer configuration review.','NM8N-125-3P/4P, NM8N-250-3P/4P':'Source pose, terminal parts and projection bounds require review before mapping; no family/CSH electrical equivalence inferred.'},'sources_are_file_links_not_unique_models':True}
 price_ids=set()
 for family in reviewed:
  profile=json.loads((CAT/'Chint/ThietBi'/('OFFICIAL-STEP-'+family)/'thong_tin_thiet_bi.json').read_text(encoding='utf8'))
  price_ids.update(o['source_row_id'] for o in profile['catalog_tham_khao']['options'] if o.get('source_row_id'))
 summary.update(reviewed_faces=len(published),linked_price_rows=len(price_ids))
 summary['review_pending']['NXM-400-630-3P-v1/v2']='Byte-identical official downloads; extra projecting components yield H=465 mm. Kept outside published CAD pending assembly/configuration review.'
 (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(summary,ensure_ascii=True))
if __name__=='__main__':main()

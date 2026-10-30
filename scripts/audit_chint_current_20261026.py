import sys,json,hashlib,collections,io,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from app.services.catalog_publication_policy import public_device_allowed
from app.services.catalog_view_health import displayable
from app.services.cad.ls_view_coverage import view_coverage
from app.api.v1.endpoints.equipment_library import _cad_view_file
from app.services.equipment_library import asset_bytes,_catalogtb_asset
from app.services.price_row_cad_detail import linked_cad_for_row
from app.services.cad.catalogtb_assets import normalized_source
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB';OUT=ROOT/'docs/chint-audit-2026-10-26';OUT.mkdir(exist_ok=True)
snapshot=json.loads((CAT/'_agent_index/browser_display_v5.json').read_text(encoding='utf8'));devices=[d for d in snapshot['items'] if str(d.get('brand','')).upper()=='CHINT' and public_device_allowed(d)];report=[];errors=[]
for d in devices:
 groups=collections.defaultdict(list);views=[]
 for v in d['views']:
  groups[v.get('cad_variant_id') or d['id']].append(v)
  try:
   relative=_cad_view_file(d['id'],v['id'],'dxf');raw=asset_bytes(relative);doc=ezdxf.read(io.StringIO(raw.decode('utf-8-sig'),newline=None));audit=doc.audit();assert doc.units==4,'not mm';assert len(doc.modelspace()),'empty CAD';assert not audit.errors and not audit.fixes,'DXF audit errors/fixes';assert displayable(v),'unresolved view'
   counts=collections.Counter(e.dxftype() for b in doc.blocks for e in b)
   views.append({'id':v['id'],'label':v.get('face') or v.get('label'),'path':str(normalized_source(_catalogtb_asset(relative)).resolve()),'relative':relative,'sha256':hashlib.sha256(raw).hexdigest(),'native_dynamic':b'BLOCKVISIBILITYPARAMETER' in raw,'entities':dict(counts),'units_mm':True})
  except Exception as exc:errors.append({'catalog_id':d['id'],'view_id':v['id'],'reason':str(exc)})
 report.append({'id':d['id'],'model':d.get('product_code'),'type':d.get('type'),'views':views,'view_sets':[{'variant_id':k,**view_coverage(vs)} for k,vs in groups.items()]});print('CAD',len(report),'/',len(devices),len(views),d.get('product_code'),flush=True)
from app.services.library_catalog_information import source_rows
prices=[r for r in source_rows() if str(r.get('brand','')).upper()=='CHINT' and r.get('information_kind')=='pricebook'];price_report=[]
for i,r in enumerate(prices):
 matches=linked_cad_for_row(r,devices);families=[{'id':m['id'],'selection_id':m['selection_id'],'views':len(m['views']),**view_coverage(m['views'])} for m in matches];price_report.append({'id':r['id'],'sku':r['sku'],'category':r.get('category'),'linked':bool(matches),'six_views':any(m['complete'] for m in families),'families':families})
 if i%200==0:print('PRICE',i,'/',len(prices),flush=True)
summary={'profiles':len(report),'views':sum(len(d['views']) for d in report),'single_view_profiles':sum(len(d['views'])==1 for d in report),'six_view_profiles':sum(any(s['complete'] for s in d['view_sets']) for d in report),'errors':errors,'price_rows':len(prices),'linked_price_rows':sum(r['linked'] for r in price_report),'six_view_price_rows':sum(r['six_views'] for r in price_report),'missing_price_rows':sum(not r['linked'] for r in price_report),'partial_price_rows':sum(r['linked'] and not r['six_views'] for r in price_report)}
(OUT/('audit-after.json' if '--after' in sys.argv else 'audit-before.json')).write_text(json.dumps({'summary':summary,'devices':report,'prices':price_report},ensure_ascii=False,indent=2),encoding='utf8');print('SUMMARY',summary,flush=True)

"""Check every profile through the agent lookup and parse every declared CAD view."""
from pathlib import Path
import sys, json, hashlib
from collections import Counter
import ezdxf

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))
sys.stdout.reconfigure(encoding='utf-8')
from app.services.device_catalog_engine import DeviceCatalogEngine
from app.services.cad import catalogtb_assets as ca
from app.services.cad.cabinet_templates import inventory, source_path

OUT=BASE.parent/'outputs/catalogtb-agent-audit'
manifest=json.loads((ca.ROOT/'ai_library_manifest.json').read_text(encoding='utf-8'))
engine=DeviceCatalogEngine.get_instance()
assets=ca.assets(refresh=True)
profiles=[]
for ref in engine.reference_profiles:
    matches=engine.search_references(ref['category'],limit=len(engine.reference_profiles))
    ranked=engine.search_references(ref['category'],query=ref['series'] or ref['name'])
    full_present=any(x['reference_path']==ref['reference_path'] for x in matches)
    profiles.append(dict(profile=ref['reference_path'],name=ref['name'],category=ref['category'],
        found_in_full_category_lookup=full_present,
        found_in_first_five_for_identity_query=any(x['reference_path']==ref['reference_path'] for x in ranked),
        exact_model_verified=False))

views=[]
for index,asset in enumerate(assets,1):
    row=dict(id=asset['id'],profile=asset['profile_path'],face=asset['face'],path=asset['path'])
    try:
        path=Path(asset['path']).resolve()
        if not path.is_relative_to(ca.ROOT.resolve()):raise ValueError('CAD outside CatalogTB')
        doc=ezdxf.readfile(path)
        audit=doc.audit()  # In memory only; never save or repair source geometry here.
        row.update(readable=True,units_code=doc.units,modelspace_entities=len(doc.modelspace()),
            audit_error_count=len(audit.errors),in_memory_fix_count=len(audit.fixes),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        row['unit_verification']=asset.get('units_evidence') or {}
        row['original_path']=asset.get('original_path')
        row['original_units_code']=row['unit_verification'].get('raw_header_units_code',doc.units)
    except Exception as exc:
        row.update(readable=False,error=str(exc)[:300])
    views.append(row)
    if index%100==0:print(f'Parsed {index}/{len(assets)} CAD views',flush=True)

forms=[]
for form in inventory():
    try:
        path=source_path(form);doc=ezdxf.readfile(path)
        forms.append(dict(id=form['id'],readable=True,entities=len(doc.modelspace())))
    except Exception as exc:forms.append(dict(id=form['id'],readable=False,error=str(exc)[:300]))

summary=dict(profiles_on_disk=len(list(ca.ROOT.rglob('thong_tin_thiet_bi.json'))),
    manifest_profiles=len(manifest['items']),agent_reference_profiles=len(profiles),
    all_category_lookup_found=sum(p['found_in_full_category_lookup'] for p in profiles),
    first_five_identity_query_found=sum(p['found_in_first_five_for_identity_query'] for p in profiles),
    function_identified=sum(p['category']!='UNCLASSIFIED' for p in profiles),
    unresolved_identity=sum(p['category']=='UNCLASSIFIED' for p in profiles),
    cad_views=len(views),readable_cad_views=sum(v['readable'] for v in views),
    cad_with_audit_errors=sum(v.get('audit_error_count',0)>0 for v in views),
    cad_with_in_memory_fixes=sum(v.get('in_memory_fix_count',0)>0 for v in views),
    unknown_faces=sum(v['face']=='unknown' for v in views),
    cad_units_not_mm=sum(v.get('units_code')!=4 for v in views),
    source_headers_normalized_without_resizing=sum(bool(v.get('unit_verification')) for v in views),
    forms=len(forms),readable_forms=sum(f['readable'] for f in forms))
report=dict(summary=summary,profiles=profiles,views=views,forms=forms,
    unresolved_by_group=dict(Counter(i['group'] for i in manifest['items'] if i['category_code']=='UNCLASSIFIED')),
    limitations=['This checks discovery, lookup, and DXF parsing; it is not an AI visual recognition benchmark.',
        'Unconfirmed category, face, unit, electrical rating, or SKU blocks automatic approval.',
        'A top-five shortlist may omit duplicate identities; use full profile identity for unambiguous selection.',
        'Checks run against saved source code; active backend version must be verified separately.'])
OUT.mkdir(exist_ok=True)
(OUT/'deep-recognition-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False),flush=True)

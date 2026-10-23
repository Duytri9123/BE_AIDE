"""Read-only audit of source files, fresh library output and explicit price links."""
import collections, csv, hashlib, json, logging, sys, time
from pathlib import Path
from xml.etree import ElementTree
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ezdxf
logging.getLogger('ezdxf').setLevel(logging.ERROR)
from app.services.ai.manufacturer_registry import canonical_brand
from app.services.catalogtb_browser import _build_browser_data
from app.services.cad.catalogtb_assets import normalized_source, face_code
from app.services.cad.ls_view_coverage import view_coverage
from app.services.customer_technical_specs import view_technical_specs

ROOT = Path(__file__).resolve().parents[1]
CAT = ROOT/'data/CatalogTB'
OUT = ROOT/'docs/abb-ls-chint-current-audit-2026-10-21'
BRANDS = {'ABB', 'LS Electric', 'CHINT'}
FOLDER_BRANDS = {'ABB':'ABB','LS':'LS Electric','Chint':'CHINT'}
DXF_CACHE_PATH = None

def save(name, value):
    (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')

def csv_rows(name, rows, columns):
    with (OUT/name).open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream); writer.writerow(columns)
        for row in rows:
            writer.writerow([json.dumps(row.get(k), ensure_ascii=False) if isinstance(row.get(k), (list,dict)) else row.get(k) for k in columns])

def main():
    OUT.mkdir(exist_ok=True)
    print('Building fresh display data from profiles (without publishing)...', flush=True)
    fresh = _build_browser_data()
    devices = [d for d in fresh['items'] if canonical_brand(d.get('brand')) in BRANDS]
    save('fresh-devices.json', {'items':devices})
    selected_ids = {d['id'] for d in devices}
    snapshots = {d['id']:d for d in json.loads((CAT/'_agent_index/browser_display_v5.json').read_text(encoding='utf8'))['items'] if canonical_brand(d.get('brand')) in BRANDS}
    profiles = []; index = collections.defaultdict(list); files = {}; errors = []; links = collections.defaultdict(list)
    for path in sorted(CAT.rglob('thong_tin_thiet_bi.json')):
        relative = path.relative_to(CAT).as_posix()
        cid = 'TB-'+hashlib.sha1(relative.encode()).hexdigest()[:16]
        raw = json.loads(path.read_text(encoding='utf-8-sig'))
        folder_brand = FOLDER_BRANDS.get(relative.split('/')[0])
        maker = canonical_brand(raw.get('hang_xac_nhan'))
        if cid not in selected_ids and not folder_brand and maker not in BRANDS:
            continue
        brand = canonical_brand(next((d['brand'] for d in devices if d['id']==cid), None)) or maker or folder_brand
        if brand not in BRANDS: brand = folder_brand
        hidden = bool(raw.get('browser_hidden')); views = []; groups = collections.defaultdict(list)
        for view in raw.get('cad_don', []):
            vid = view['id_hinh_goc']; source = path.parent/view.get('duong_dan',''); problems = []
            record = {'profile_id':cid,'profile':relative,'brand':brand,'hidden':hidden,'id':vid,'face':view.get('huong_nhin'),'variant':view.get('bien_the_cad') or view.get('bien_the') or 'default'}
            if not source.is_file(): problems.append('missing_dxf')
            else:
                try:
                    drawing = normalized_source(source)
                    if not drawing.resolve().is_relative_to(CAT.resolve()): raise ValueError('outside catalog')
                    record['path'] = drawing.relative_to(CAT).as_posix()
                    files.setdefault(str(drawing.resolve()), []).append(record)
                except Exception as exc: problems.append('unit_or_path_contract: '+str(exc))
            preview = source.with_name('xem_truoc.svg')
            if not preview.is_file(): problems.append('missing_preview')
            else:
                try: ElementTree.parse(preview)
                except Exception as exc: problems.append('invalid_svg: '+str(exc))
            if not view.get('huong_nhin') or face_code(view.get('huong_nhin'))=='unknown' or 'chưa xác' in str(view.get('nhan_hien_thi') or view.get('huong_nhin')).lower(): problems.append('unresolved_face')
            record['issues'] = problems; views.append(record)
            groups[record['variant']].append({**view,'available':source.is_file()})
            if not hidden: index[vid].append(record)
            for issue in problems: errors.append({**record,'error':issue})
        sets = [view_coverage(values) for values in groups.values()]
        row = {'brand':brand,'profile_id':cid,'profile':relative,'name':raw.get('ten_san_pham'),'hidden':hidden,'view_count':len(views),'visible_primary_item':cid in selected_ids,'views':views,'complete_six':any(s['complete'] for s in sets)}
        profiles.append(row)
        if not hidden:
            for option in (raw.get('catalog_tham_khao') or {}).get('options',[]):
                if option.get('source_row_id') and canonical_brand(option.get('brand'))==brand:
                    links[option['source_row_id']].append(row)
    print(f'Collected {len(profiles)} profiles / {len(files)} unique DXF files; parsing...', flush=True)
    parsed = []
    prior_files={r['path']:r for r in json.loads(DXF_CACHE_PATH.read_text(encoding='utf8'))} if DXF_CACHE_PATH and DXF_CACHE_PATH.is_file() else {}
    for number, (path, references) in enumerate(files.items(), 1):
        result = {'path':Path(path).relative_to(CAT.resolve()).as_posix(),'references':len(references),'brands':sorted({r['brand'] for r in references if r['brand']}),'all_references_hidden':all(r['hidden'] for r in references)}
        try:
            digest=hashlib.sha256(Path(path).read_bytes()).hexdigest();prior=prior_files.get(result['path'])
            if prior and prior.get('sha256')==digest and not prior.get('issues') and not prior.get('in_memory_fixes'):
                result.update({k:prior[k] for k in ('units','entities','audit_errors','in_memory_fixes','sha256','issues')});result['unchanged_sha256_reused']=True
            else:
                doc = ezdxf.readfile(path); audit = doc.audit()
                result.update(units=doc.units, entities=len(doc.modelspace()), audit_errors=len(audit.errors), in_memory_fixes=len(audit.fixes), sha256=digest)
                problems = []
                if doc.units!=4: problems.append('not_millimetres')
                if not len(doc.modelspace()): problems.append('empty_dxf')
                if audit.errors: problems.append('dxf_audit_errors')
                result['issues'] = problems
        except Exception as exc: result['issues'] = ['unreadable_dxf: '+str(exc)]
        for issue in result['issues']:
            errors.extend({**r,'error':issue} for r in references)
        parsed.append(result)
        if number%100==0: print(f'Parsed {number}/{len(files)}', flush=True)
    items = []; summary = collections.defaultdict(collections.Counter)
    for device in devices:
        brand = canonical_brand(device['brand']); groups = collections.defaultdict(list); unresolved = []; measurements = 0
        for view in device['views']:
            sources = index.get(view['id'],[])
            preferred = [s for s in sources if s['profile_id'] in {device['id'],*(device.get('member_profile_ids') or [])}]
            sources = preferred or sources
            variants = {s['profile_id']+':'+s['variant'] for s in sources}
            variant = view.get('cad_variant_id') or (next(iter(variants)) if len(variants)==1 else 'unpaired:'+view['id'])
            groups[variant].append({**view,'available':bool(sources) and any('path' in s for s in sources)})
            if face_code(view.get('face'))=='unknown': unresolved.append(view['id'])
            measurements += bool(view_technical_specs(device,view['id']))
        coverage = [view_coverage(values) for values in groups.values()]
        best = min(coverage,key=lambda s:len(s['missing_faces'])) if coverage else view_coverage([])
        old = snapshots.get(device['id']); old_ids = {v['id'] for v in (old or {}).get('views',[])}; new_ids = {v['id'] for v in device['views']}
        identity = []
        if device.get('brand_identification_status')!='verified': identity.append('manufacturer_not_verified')
        if not device.get('product_code'): identity.append('missing_model')
        if str(device.get('type') or '').upper() in {'UNKNOWN','UNCLASSIFIED','SOURCE_REFERENCE','ASSEMBLY_REFERENCE'}: identity.append('reference_or_unclassified_item')
        identification = (device.get('catalog_references') or {}).get('source_identification') or {}
        row = {'brand':brand,'id':device['id'],'name':device['display'],'type':device.get('type'),'model':device.get('product_code'),'view_count':len(device['views']),'complete_six':any(s['complete'] for s in coverage),'missing_faces':best['missing_labels'],'unresolved_faces':unresolved,'identity_review':identity,'exact_ordering_code_verified':identification.get('ordering_code_verified') is True,'geometry_verified':identification.get('geometry_verified') is True,'views_with_measurements':measurements,'not_in_snapshot':old is None,'snapshot_view_set_differs':old_ids!=new_ids,'auto_select':device.get('auto_select')}
        items.append(row); count = summary[brand]
        count['visible_items']+=1;count['visible_views']+=len(device['views']);count['one_view_items']+=len(device['views'])==1;count['complete_six_items']+=row['complete_six'];count['incomplete_six_items']+=not row['complete_six'];count['unknown_face_items']+=bool(unresolved);count['identity_review_items']+=bool(identity);count['no_measurement_items']+=measurements==0;count['snapshot_differences']+=row['not_in_snapshot'] or row['snapshot_view_set_differs'];count['not_exact_ordering_code_verified']+=not row['exact_ordering_code_verified']
    prices = json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items']; price_rows = []
    for price in prices:
        brand = canonical_brand(price.get('brand'))
        if brand not in BRANDS: continue
        matches = [p for p in links.get(price['id'],[]) if p['brand']==brand and p['view_count']]
        status = 'six_view_family_reference' if any(p['complete_six'] for p in matches) else 'linked_incomplete_views' if matches else 'no_explicit_cad_link'
        price_rows.append({'brand':brand,'sku':price['sku'],'price_row_id':price['id'],'category':price.get('category'),'status':status,'profiles':[p['profile'] for p in matches]})
        summary[brand]['price_rows']+=1; summary[brand]['price_'+status]+=1
    save('profiles.json',profiles);save('dxf-files.json',parsed);save('items.json',items);save('issues.json',errors);save('pricebook-coverage.json',price_rows)
    csv_rows('missing-views.csv',[r for r in items if not r['complete_six']],['brand','id','name','type','view_count','missing_faces'])
    csv_rows('identity-review.csv',[r for r in items if r['identity_review']],['brand','id','name','type','model','identity_review'])
    csv_rows('pricebook-without-explicit-cad.csv',[r for r in price_rows if r['status']=='no_explicit_cad_link'],['brand','sku','price_row_id','category','status'])
    csv_rows('file-errors.csv',errors,['brand','profile','id','face','hidden','error'])
    report = {'checked_at':time.strftime('%Y-%m-%d %H:%M:%S'),'brands':summary,'source_profiles':len(profiles),'hidden_profiles':sum(p['hidden'] for p in profiles),'active_profiles_without_cad':[p['profile'] for p in profiles if not p['hidden'] and not p['view_count']],'unique_dxf_files':len(parsed),'readable_dxf_files':sum(not any(x.startswith('unreadable') for x in p['issues']) for p in parsed),'dxf_files_with_errors':sum(bool(p['issues']) for p in parsed),'dxf_files_with_in_memory_fixes':sum(bool(p.get('in_memory_fixes')) for p in parsed),'issue_counts':collections.Counter(e['error'] for e in errors),'active_issue_counts':collections.Counter(e['error'] for e in errors if not e['hidden']),'snapshot_only_ids':sorted(set(snapshots)-{d['id'] for d in devices}),'limits':['Six directions counted per variant; missing optional views is a coverage gap, not evidence of corrupt geometry.','No explicit source_row_id link is an unverified pricebook linkage, not proof that no related CAD exists.','Structural parsing and metadata checks do not certify visual direction or exact SKU/coil/terminal/electrical compatibility.','DXF audit changes are in memory only; no source CAD repaired or deleted.']}
    save('summary.json',report);print(json.dumps(report,ensure_ascii=True),flush=True)

if __name__=='__main__':main()

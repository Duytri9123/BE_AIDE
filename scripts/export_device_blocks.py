"""Export all commercial rows and all available CAD views as shared viewer JSON.

Run with the backend interpreter. Geometry is deduplicated, not copied per SKU.
"""
import argparse
import hashlib
import gzip
import json
import sys
import logging
import multiprocessing
logging.getLogger('ezdxf').setLevel(logging.ERROR)
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.library_catalog_information import source_rows
from app.services.catalogtb_browser import browser_data
from app.services.customer_equipment_information import customer_information_rows, public_view_id
from app.services.equipment_library import get_equipment, _catalogtb_asset
from app.services.cad.catalogtb_assets import face_code
from app.services.cad.device_block_package import block_package, public_row_id, ENVELOPES
from app.services.cad.price_device_projection import price_device_projections, _projection


def projection_cache_path(path,stamp):
    key=hashlib.sha256(f'{path}:{stamp}:visible-v2'.encode()).hexdigest()
    return Path(__file__).resolve().parents[1]/'data/device_block_geometry'/(key+'.json')


def compute_projection(path,stamp):
    try:_projection(path,stamp)
    except Exception as exc:projection_cache_path(path,stamp).with_suffix('.failure.json').write_text(json.dumps({'error':type(exc).__name__}),encoding='utf8')


def cached_projection(path,stamp):
    stored=projection_cache_path(path,stamp)
    compressed=stored.with_suffix('.json.gz')
    if compressed.is_file():
        with gzip.open(compressed,'rt',encoding='utf8') as stream:return json.load(stream)
    if not stored.is_file():raise ValueError('Nguồn CAD cần mở trực tiếp trong CAD Viewer; chưa có nét JSON chuyển đổi được.')
    return json.loads(stored.read_text(encoding='utf8'))


def project_task(task):
    index,path,stamp,view_id,face,label=task
    try:
        if projection_cache_path(path,stamp).with_suffix('.failure.json').is_file():raise ValueError('Nguồn cần kiểm tra lại.')
        if not projection_cache_path(path,stamp).is_file() and not projection_cache_path(path,stamp).with_suffix('.json.gz').is_file():
            raw=Path(path).read_bytes()
            simple=len(raw)<100000 and not any(kind in raw for kind in (b'HATCH',b'REGION',b'3DSOLID',b'ACISDATA'))
            if simple:
                compute_projection(path,stamp)
                _projection.cache_clear()
            else:
                process=multiprocessing.get_context('spawn').Process(target=compute_projection,args=(path,stamp))
                process.start();process.join(12)
                if process.is_alive():
                    process.terminate();process.join();projection_cache_path(path,stamp).with_suffix('.failure.json').write_text('{"error":"TimeoutError"}',encoding='utf8');raise TimeoutError('Mặt CAD phức tạp: giữ liên kết DXF gốc.')
        value=cached_projection(path,stamp)
        return index,{**value,'view_id':view_id,'face':face,'label':label},None
    except Exception as exc:
        return index,None,type(exc).__name__


def export(target,reuse_cad=False):
    target.mkdir(parents=True, exist_ok=True)
    (target / 'geometry').mkdir(exist_ok=True)
    (target / 'rows').mkdir(exist_ok=True)
    stats = dict(rows=0, source_cad_rows=0, draft_rows=0, cad_profiles=0, source_views=0, geometry_files=0)
    errors = []

    def write(path, value):
        path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')), encoding='utf8')

    verified=set()
    def reference(view):
        if not view or not view.get('paths'):
            return view
        geometry = {k: view[k] for k in ('paths', 'width', 'height', 'units', 'origin_mm', 'sha256', 'visibility') if k in view}
        blob = json.dumps(geometry, ensure_ascii=False, separators=(',', ':'))
        key = hashlib.sha256(blob.encode()).hexdigest()[:32]
        path = target / 'geometry' / (key + '.json.gz')
        if path.exists() and key not in verified:
            try:
                with gzip.open(path,'rb') as stream:
                    digest=hashlib.file_digest(stream,'sha256').hexdigest()[:32]
                if digest!=key:path.unlink()
            except (OSError,EOFError):path.unlink()
        if not path.exists():
            with gzip.open(path,'wt',encoding='utf8',compresslevel=6) as stream:stream.write(blob)
            stats['geometry_files'] += 1
        verified.add(key)
        return {**{k: v for k, v in view.items() if k != 'paths'}, 'geometry_ref': 'geometry/' + key + '.json.gz'}

    devices = browser_data()['items']
    # Warm the same projection cache used by the API; preserve every labelled view.
    profiles = []
    linked = defaultdict(list)
    tasks=[]
    for device in devices:
        for row_id in {o.get('source_row_id') for o in (device.get('catalog_references') or {}).get('options', [])}:
            if row_id:
                linked[row_id].append(device)
        record = get_equipment(device['id'])
        profiles.append(dict(id=device['id'], name=device.get('display'), brand=device.get('brand'), views=[]))
        for view in (record or {}).get('cad', {}).get('views', []):
            path = _catalogtb_asset((view.get('dxf') or {}).get('path', ''))
            if not path:
                profiles[-1]['views'].append(dict(view_id=public_view_id(view['id']),face=face_code(view.get('name') or view.get('state')),label=view.get('name') or view.get('state'),geometry_status='source_reference'))
            if path:
                tasks.append((len(profiles)-1, str(path), path.stat().st_mtime_ns, public_view_id(view['id']),
                              face_code(view.get('name') or view.get('state')), view.get('name') or view.get('state')))
    if reuse_cad:
        profiles=json.loads((target/'cad-profiles.json').read_text(encoding='utf8'))
        assert len(profiles)==len(devices)
        stats['source_views']=sum(bool(v.get('geometry_ref')) for p in profiles for v in p['views'])
    else:
        for i, task in enumerate(tasks):
            index,geometry,error=project_task(task)
            if error:
                errors.append(dict(profile=profiles[index]['id'],reason=error))
                task=tasks[i]
                profiles[index]['views'].append(dict(view_id=task[3],face=task[4],label=task[5],geometry_status='source_reference',dxf_url='/equipment-library/'+profiles[index]['id']+'/views/'+task[3]+'/dxf'))
            else:
                profiles[index]['views'].append(reference(geometry))
                stats['source_views']+=1
            if i%50==0:
                stats['cad_profiles']=sum(bool(p['views']) for p in profiles)
                write(target/'progress.json',stats)
                print('CAD views',i,'/',len(tasks),flush=True)
    stats['cad_profiles']=len(profiles)
    write(target / 'cad-profiles.json', profiles)

    import app.services.cad.price_device_projection as projection_service
    by_view={(p['id'],v['view_id']):v for p in profiles for v in p['views'] if v.get('geometry_ref')}
    metadata={(path,stamp):by_view[(profiles[index]['id'],view_id)] for index,path,stamp,view_id,face,label in tasks if (profiles[index]['id'],view_id) in by_view}
    def metadata_projection(path,stamp):
        result=metadata.get((path,stamp))
        if result is None:raise ValueError('Mặt cần kiểm tra nguồn trong CAD Viewer.')
        return result
    projection_service._projection=metadata_projection
    shards = defaultdict(dict)
    for i, row in enumerate(source_rows()):
        public_id = public_row_id(row)
        try:
            if linked.get(row['id']):
                package = price_device_projections(public_id, [row], linked[row['id']])
            else:
                product = customer_information_rows([{**row, 'information_kind': 'pricebook'}], {'brand': row['brand']})
                if not product:
                    product = [{k: row.get(k) for k in ('sku', 'name', 'item_name', 'brand', 'category')}]
                package = block_package({**product[0], 'id': public_id}, [])
            for candidate in package['candidates']:
                for face in ('front', 'side', 'top'):
                    if candidate.get(face):
                        candidate[face] = reference(candidate[face])
                candidate['projections'] = [reference(v) for v in candidate.get('projections', [])]
            shards[public_id[:2]][public_id] = package
            stats['rows'] += 1
            stats['source_cad_rows' if package['geometry_status'] == 'source_cad' else 'draft_rows'] += 1
        except Exception as exc:
            product = {k: row.get(k) for k in ('sku', 'name', 'item_name', 'brand', 'category')}
            package = block_package({**product, 'id': public_id}, [])
            shards[public_id[:2]][public_id] = package
            stats['rows'] += 1
            stats['draft_rows'] += 1
            errors.append(dict(row=public_id, reason=str(exc)))
        if i % 500 == 0:
            print('Rows', i, flush=True)
    stats['geometry_files']=len(list((target/'geometry').glob('*.json.gz')))
    for prefix, rows in shards.items():
        write(target / 'rows' / (prefix + '.json'), rows)
    write(target / 'manifest.json', dict(schema_version=2, contract='aide.cad-device-block',
          stats=stats, row_shards='rows/{first_two_id_characters}.json',
          draft_dimensions_verified=False, envelope_defaults=ENVELOPES, errors=errors))
    print(json.dumps(stats), 'errors', len(errors), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reuse-cad',action='store_true')
    args=parser.parse_args()
    export(args.output.resolve(),args.reuse_cad)

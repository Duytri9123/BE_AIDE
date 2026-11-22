"""Validate exported row coverage/references and refresh draft-only envelopes."""
import argparse
import hashlib
import gzip
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.library_catalog_information import source_rows
from app.services.catalogtb_browser import browser_data
from app.services.customer_equipment_information import public_view_id
from app.services.cad.catalogtb_assets import face_code
from app.services.cad.device_block_package import draft_block,public_row_id,block_package


def check(target):
    target=target.resolve()
    manifest=json.loads((target/'manifest.json').read_text(encoding='utf8'))
    seen=set();used=set();native=draft=0

    def refs(value):
        if isinstance(value,dict):
            if value.get('geometry_ref'):
                ref=value['geometry_ref'];path=(target/ref).resolve()
                assert path.is_relative_to(target/'geometry') and path.is_file(),ref
                used.add(path.name)
            for v in value.values():refs(v)
        elif isinstance(value,list):
            for v in value:refs(v)

    profiles=json.loads((target/'cad-profiles.json').read_text(encoding='utf8'));refs(profiles)
    for profile in profiles:
        unique={}
        for view in profile['views']:
            if view['view_id'] not in unique or view.get('geometry_ref'):unique[view['view_id']]=view
        profile['views']=list(unique.values())
    by_id={p['id']:p for p in profiles}
    for device in browser_data()['items']:
        profile=by_id[device['id']];known={v['view_id'] for v in profile['views']}
        for view in device.get('views',[]):
            key=public_view_id(view['id'])
            if key not in known:
                known.add(key)
                profile['views'].append(dict(view_id=key,face=face_code(view.get('face') or view.get('label')),label=view.get('label'),geometry_status='source_reference',dxf_url=str(view.get('download') or '').replace('/views/'+view['id']+'/', '/views/'+key+'/')))
    (target/'cad-profiles.json').write_text(json.dumps(profiles,ensure_ascii=False,separators=(',',':')),encoding='utf8')
    source_refs=sum(v.get('geometry_status')=='source_reference' for p in profiles for v in p['views'])
    for shard in (target/'rows').glob('*.json'):
        packages=json.loads(shard.read_text(encoding='utf8'))
        changed=False
        for row_id,package in packages.items():
            assert row_id not in seen;seen.add(row_id)
            assert package['product']['id']==row_id and package['candidates']
            if package['geometry_status']=='parametric_unverified':
                package['candidates']=[draft_block(package['product'])];draft+=1;changed=True
            else:
                enriched=block_package(package['product'],package['candidates'])
                if enriched['candidates']!=package['candidates']:package['candidates']=enriched['candidates'];changed=True
                native+=1
            refs(package)
        if changed:shard.write_text(json.dumps(packages,ensure_ascii=False,separators=(',',':')),encoding='utf8')
    assert seen=={public_row_id(r) for r in source_rows()},'Missing/extra commercial rows'
    for name in used:
        path=target/'geometry'/name
        with gzip.open(path,'rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()[:32]
        assert name.startswith(digest),name
    # Preserve valid historical hashes: saved projects may still refer to them.
    # Only interrupted export files with an invalid digest are disposable.
    for path in (target/'geometry').glob('*.json.gz'):
        if path.name not in used:
            valid=False
            try:
                with gzip.open(path,'rb') as stream:valid=path.name.startswith(hashlib.file_digest(stream,'sha256').hexdigest()[:32])
            except (OSError,EOFError):pass
            if not valid:
                assert path.resolve().is_relative_to(target/'geometry');path.unlink()
    result=dict(rows=len(seen),source_cad_rows=native,draft_rows=draft,cad_profiles=len(profiles),
                source_views=sum(len(p['views']) for p in profiles)-source_refs,source_reference_views=source_refs,
                geometry_files=len(used),validated=True)
    manifest['stats']=result
    (target/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':')),encoding='utf8')
    progress=target/'progress.json'
    if progress.is_file():progress.unlink()
    print(json.dumps(result))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path)
    check(parser.parse_args().directory)

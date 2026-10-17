"""Audit every source folder; keep private evidence out of the public summary."""
import hashlib
import json
from collections import Counter,defaultdict
from pathlib import Path
from app.services.equipment_library import CATALOG_TB_ROOT
from app.services.catalogtb_browser import _build_browser_data
from app.services.customer_equipment_information import product_specs
from app.services.ai.manufacturer_registry import canonical_brand

ROOT=Path(__file__).resolve().parents[1]


def main():
    folders=defaultdict(Counter);private=[]
    for folder in CATALOG_TB_ROOT.iterdir():
        if folder.is_dir() and folder.name!='_agent_index':
            folders[folder.name].update(profiles=0,view_uses=0)
    for path in sorted(CATALOG_TB_ROOT.rglob('thong_tin_thiet_bi.json')):
        relative=path.relative_to(CATALOG_TB_ROOT);folder=relative.parts[0]
        counts=folders[folder];counts['profiles']+=1
        try:raw=json.loads(path.read_text(encoding='utf-8-sig'))
        except (ValueError,OSError) as e:
            counts['unreadable_profiles']+=1;private.append({'profile':relative.as_posix(),'error':str(e)});continue
        counts['hidden_profiles' if raw.get('browser_hidden') else 'active_source_profiles']+=1
        views=raw.get('cad_don') or [];counts['view_uses']+=len(views)
        if len(views)==1:counts['single_view_profiles']+=1
        issues=[]
        for view in views:
            drawing=(path.parent/view.get('duong_dan','')).resolve()
            if not drawing.is_relative_to(CATALOG_TB_ROOT.resolve()):
                counts['invalid_asset_paths']+=1;issues.append('invalid_asset_path');continue
            for asset,key in ((drawing,'missing_dxf'),(drawing.with_name('xem_truoc.svg'),'missing_preview')):
                if not asset.is_file():counts[key]+=1;issues.append(key)
            if not (view.get('nhan_dien_mat') or {}).get('method'):counts['views_without_individual_review']+=1
        if issues:private.append({'profile':relative.as_posix(),'issues':issues})
    browser=_build_browser_data();families=defaultdict(list)
    for p in browser['items']:
        if p.get('product_code') and p.get('brand'):
            families[(canonical_brand(p['brand']),p['product_code'].strip().casefold(),p.get('type'))].append(p)
    pending=[]
    for (brand,code,kind),members in families.items():
        if len(members)<2:continue
        configs={json.dumps(product_specs(p.get('spec')),sort_keys=True,ensure_ascii=False) for p in members}
        poles={str((p.get('spec') or {}).get('so_cuc') or '') for p in members}
        reason='different_configurations' if len(configs)>1 else 'repeated_or_unverified_faces'
        if len(poles)>1 and '' not in poles:reason='different_pole_variants'
        pending.append({'brand':brand,'model':members[0]['product_code'],'type':kind,'records':len(members),'reason':reason})
    summary={'folders_checked':len(folders),'profiles_checked':sum(c['profiles'] for c in folders.values()),
             'source_view_uses':sum(c['view_uses'] for c in folders.values()),'browser_devices':browser['total'],
             'browser_views':browser['view_count'],'folders':[{'name':name,**dict(c)} for name,c in sorted(folders.items())],
             'repeated_model_groups':pending,
             'scope':'All profile folders scanned. Asset integrity and grouping audit; individual projection geometry and exact order-code verification are not implied.'}
    (ROOT/'tmp/catalog-folder-audit').mkdir(parents=True,exist_ok=True)
    (ROOT/'tmp/catalog-folder-audit/private-issues.json').write_text(json.dumps(private,ensure_ascii=False,indent=2),encoding='utf8')
    (ROOT/'docs/all-folders-catalog-audit.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in summary.items() if k not in {'folders','repeated_model_groups'}},ensure_ascii=False),flush=True)
    print('Integrity issues:',len(private),'Repeated model groups:',len(pending),flush=True)


if __name__=='__main__':main()

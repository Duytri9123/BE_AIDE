"""Compare serialized CAD geometry so AutoCAD runtime metadata cannot create duplicates."""
import json,re,shutil,sys
from pathlib import Path
import ezdxf
from update_supplied_brand_libraries import visible,fingerprint,read,save,BASE,ROOT
brand=sys.argv[1];report_path=ROOT/brand/'kiem_tra_nguon_bo_sung.json';report=read(report_path)
cache=read(BASE/'tmp/brand_update/existing_geometry_v2.json')
def units(path):
    with path.open('rb') as stream:header=stream.read(20000).decode('ascii','ignore')
    match=re.search(r'\$INSUNITS\s+70\s+(\d+)',header)
    return int(match[1]) if match else 0
known={(units(ROOT/paths[0]),k):paths[0] for k,paths in cache.items() if paths and all('/SRC_' not in p for p in paths) and (ROOT/paths[0]).exists()}
kept=[];archive=BASE/'tmp/brand_update/serialized_duplicates'/brand;archive.mkdir(parents=True,exist_ok=True)
for item in report['added']:
    path=ROOT/item['profile'];folder=path.parent;doc=ezdxf.readfile(folder/'CadChenTu/ban_ve.dxf')
    geometry_key=fingerprint(list(visible(doc,doc.modelspace())))
    key=(doc.units,geometry_key)
    if key in known:
        target=ROOT/known[key];target_profile=target.parents[2]/'thong_tin_thiet_bi.json'
        profile=read(path)
        report['duplicates'].append({'source':profile['nguon_cad'],'existing':[known[key]],'basis':'Serialized CAD geometry matches after omitting nongeometric AutoCAD metadata'})
        if target_profile.parent.name.startswith('SRC_'):
            d=read(target_profile)
            d.setdefault('nguon_cad_cung_hinh',[]).append(profile['nguon_cad'])
            d['tu_khoa_tim_kiem']=list(dict.fromkeys(d.get('tu_khoa_tim_kiem',[])+profile.get('tu_khoa_tim_kiem',[])))
            save(target_profile,d)
        assert folder.resolve().is_relative_to(ROOT.resolve())
        old=(folder/'CadDon'/item['id']/'ban_ve.dxf').relative_to(ROOT).as_posix()
        for cached_key,paths in cache.items():
            if old in paths:cache[cached_key]=[known[key] if path==old else path for path in paths]
        shutil.move(str(folder),str(archive/folder.name))
    else:
        known[key]=(folder/'CadDon'/item['id']/'ban_ve.dxf').relative_to(ROOT).as_posix();kept.append(item)
        cache.setdefault(geometry_key,[]).append(known[key])
report['added']=kept;report.pop('verification',None);save(report_path,report)
save(BASE/'tmp/brand_update/existing_geometry_v2.json',cache)
print(brand,'unique new CAD',len(kept),'duplicate source references',len(report['duplicates']),flush=True)

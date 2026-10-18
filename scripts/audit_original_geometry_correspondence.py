"""Find exact translated primitive matches; never infer ordering from geometry."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import ezdxf
from ezdxf import recover
from ezdxf.disassemble import recursive_decompose

ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'data/CatalogTB'


def signature(entities):
    rows=[]; anchors=[]
    for e in recursive_decompose(entities):
        kind=e.dxftype()
        if kind in {'TEXT','MTEXT','ATTRIB','ATTDEF','POINT'}:continue
        if kind=='LINE':
            points=[tuple(e.dxf.start),tuple(e.dxf.end)]; extra=[]
        elif kind in {'CIRCLE','ARC'}:
            points=[tuple(e.dxf.center)];extra=[e.dxf.radius]
            if kind=='ARC':extra.extend([e.dxf.start_angle,e.dxf.end_angle])
        elif kind=='LWPOLYLINE':
            points=[(p[0],p[1],float(e.dxf.elevation)) for p in e.get_points()]
            extra=[bool(e.closed),*[list(p[2:]) for p in e.get_points()]]
        else:return None
        anchors.extend(points);rows.append((kind,points,extra))
    if len(rows)<6:return None
    origin=[min(p[i] for p in anchors) for i in range(3)]
    def rounded(v):
        if isinstance(v,(list,tuple)):return [rounded(x) for x in v]
        return round(v,5) if isinstance(v,float) else v
    normalized=[]
    for kind,points,extra in rows:
        shifted=rounded([[p[i]-origin[i] for i in range(3)] for p in points])
        if kind=='LINE':shifted.sort()
        normalized.append(json.dumps([kind,shifted,rounded(extra)],sort_keys=True))
    return hashlib.sha256('\n'.join(sorted(normalized)).encode()).hexdigest()


def main():
    recovered=False
    try:source=ezdxf.readfile(ROOT/'outputs/original-catalog-identity.dxf')
    except ezdxf.DXFError:
        try:source,auditor=recover.readfile(ROOT/'outputs/original-catalog-identity.dxf')
        except ezdxf.DXFError as error:
            result={'status':'conversion_invalid_for_geometry_matching','error':str(error),
                    'matched_profiles':0,'identity_verified':False,'source_modified':False}
            (ROOT/'docs/catalog-original-geometry-audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
            print(json.dumps(result),flush=True)
            return
        recovered=True
        print(f'Recovery required: {len(auditor.errors)} errors, {len(auditor.fixes)} fixes; matches remain leads only',flush=True)
    index=defaultdict(list)
    for block in source.blocks:
        try:key=signature(block)
        except Exception:continue
        if key:index[key].append(block.name)
    print(f'Indexed {sum(map(len,index.values()))} original block geometries',flush=True)
    scans=json.loads((ROOT/'docs/catalog-source-text-evidence.json').read_text(encoding='utf8'))
    results=[]
    for n,scan in enumerate(scans['items'],1):
        for view in scan['views']:
            try:key=signature(ezdxf.readfile(CAT/view['path']).modelspace())
            except Exception:key=None
            if key and key in index:
                results.append({'profile':scan['profile'],'view':view['id'],'blocks':index[key],
                    'basis':'exact_translation_normalized_primitive_geometry','identity_verified':False})
        if n%200==0:print(f'Compared {n}/{len(scans["items"])} profiles',flush=True)
    result={'matched_views':len(results),'matched_profiles':len({r['profile'] for r in results}),
        'conversion_required_recovery':recovered,
        'source_dxf_sha256':hashlib.sha256((ROOT/'outputs/original-catalog-identity.dxf').read_bytes()).hexdigest(),
        'items':results,'identity_verified':False,
        'limitation':'Geometry correspondence is a lead only; shared shapes and dynamic states do not prove a unique model.'}
    (ROOT/'docs/catalog-original-geometry-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='items'}),flush=True)


if __name__=='__main__':main()

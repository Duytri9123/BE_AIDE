"""Measure source visible envelopes and gaps; never treat these as clearances certified by a vendor."""
from pathlib import Path
import json
import math
import ezdxf

ROOT=Path(__file__).resolve().parents[2]
rows=json.loads((ROOT/'outputs/order-447-457-audit/cad-face-occurrences.json').read_text(encoding='utf8'))
result=[]
for order in ('447','457'):
    groups={}
    for row in rows:
        box=row.get('visible_bounds_mm')
        if row['order']!=order or not row.get('owner_face') or not box:continue
        key=(row.get('panel'),row['owner_face'])
        groups.setdefault(key,[]).append(row)
    for (panel,face),devices in groups.items():
        measurements=[];gaps=[]
        for row in devices:
            x0,y0,x1,y1=row['visible_bounds_mm']
            measurements.append({'handle':row['handle'],'name':row['effective_name'],
                'bounds_mm':[x0,y0,x1,y1],'width_mm':round(x1-x0,3),'height_mm':round(y1-y0,3),
                'dynamic_state':row.get('properties',{})})
        for i,a in enumerate(devices):
            ax0,ay0,ax1,ay1=a['visible_bounds_mm']
            for b in devices[i+1:]:
                bx0,by0,bx1,by1=b['visible_bounds_mm']
                horizontal=max(ax0,bx0)-min(ax1,bx1)
                vertical=max(ay0,by0)-min(ay1,by1)
                if vertical<0 and horizontal>=0:
                    gaps.append({'a':a['handle'],'b':b['handle'],'axis':'horizontal','gap_mm':round(horizontal,3)})
                elif horizontal<0 and vertical>=0:
                    gaps.append({'a':a['handle'],'b':b['handle'],'axis':'vertical','gap_mm':round(vertical,3)})
        result.append({'order':order,'panel':panel,'face':face,'devices':measurements,
            'nearest_aligned_gaps':sorted(gaps,key=lambda r:r['gap_mm'])[:40]})
dimensions=[]
for order in ('447','457'):
    doc=ezdxf.readfile(ROOT/f'outputs/sample-cad-recovery/{order}/source.dxf')
    for entity in doc.modelspace().query('DIMENSION'):
        p,q=entity.dxf.get('defpoint2'),entity.dxf.get('defpoint3')
        if p is None or q is None:continue
        dx,dy=abs(p.x-q.x),abs(p.y-q.y)
        if min(dx,dy)>0.01:continue
        measured=math.hypot(dx,dy)
        dimensions.append({'order':order,'handle':entity.dxf.handle,'axis':'horizontal' if dx>dy else 'vertical',
            'endpoint_distance_mm':round(measured,3),'points':[[p.x,p.y],[q.x,q.y]],
            'text_override':entity.dxf.get('text',''),'drawing_units':doc.units,
            'interpretation':'dimension geometry; cabinet/body/base assignment requires matching face'})
out=ROOT/'outputs/sample-cad-recovery/source-spacing-audit.json'
out.write_text(json.dumps({'units':'mm','basis':'source visible CAD bounds; includes only identified INSERTs',
    'limitations':['Exploded devices require separate measurement','Envelope gaps are not insulation or wiring clearances','Mounting holes and rebate datums require source section verification'],
    'groups':result,'source_dimensions':dimensions},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'groups':len(result),'measured_views':sum(len(g['devices']) for g in result)}))

"""Reference mining, never approval labels: modern manifests + sampled legacy DXF."""
import collections
import hashlib
import json
import re
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from ezdxf import bbox

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs/cabinet-engineering-v2-20261124'
OUT.mkdir(parents=True,exist_ok=True)
modern=ROOT/'BE_AIDE/data/CatalogTB/Form tủ/Mau'
records=[];counts=collections.Counter();names=collections.Counter()
for path in sorted(modern.glob('*/bo_tri_goc.json')):
    data=json.loads(path.read_text(encoding='utf-8'))
    roles=collections.Counter(o['role'] for o in data.get('layout_occurrences',[]));counts.update(roles)
    electrical=[o for o in data.get('layout_occurrences',[]) if o['role'] in ('device','terminal','lamp','duct','electrical_accessory')]
    names.update(o['block_name'] for o in electrical)
    records.append({'form_id':path.parent.name,'name':data.get('cabinet_name'),'roles':dict(roles),'electrical_block_names':dict(collections.Counter(o['block_name'] for o in electrical)),
                    'source':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'claim':'cooccurrence_only_not_BOM_or_clearance_verification'})

legacy=Path('D:/data/cabinet_templates/formtu')
manifest=json.loads((legacy/'manifest.json').read_text(encoding='utf-8'))
entries=manifest['items']
# Stratify by source size/kind and entity count, rather than inspect one cabinet repeatedly.
groups=collections.defaultdict(list)
for item in entries:
    dims=item.get('dimensions') or {}
    groups[(item.get('kind'),round(dims.get('height',0)/300))].append(item)
selected=[]
for group in groups.values():
    selected.extend(sorted(group,key=lambda x:x.get('entity_count',0),reverse=True)[:2])
selected=selected[:28]
samples=[]
for item in selected:
    path=legacy/item['filename'];doc=ezdxf.readfile(path);cache=bbox.Cache();devices=[]
    for ent in doc.modelspace().query('INSERT'):
        name=ent.dxf.name
        if not re.search(r'BKN|BKH|MCCB|MCB|ABN\d|ABS\d|CVS\d|cầu\s*chì|fuse|RT18|RT28|cầu\s*đấu|terminal|contactor|tiếp\s*địa',name,re.I):continue
        try:
            extent=bbox.extents([ent],cache=cache)
            if not extent.has_data:continue
            x,y=extent.extmin.x,extent.extmin.y;w,h=extent.size.x,extent.size.y
            if not (0<w<1000 and 0<h<1000):continue
            devices.append(dict(handle=ent.dxf.handle,block=name,x=x,y=y,width=w,height=h,rotation=ent.dxf.rotation))
        except Exception:continue
    gaps=[]
    for a in devices:
        for b in devices:
            if a['x']>=b['x'] or abs(a['y']+a['height']/2-b['y']-b['height']/2)>2:continue
            gap=b['x']-a['x']-a['width']
            if -.2<=gap<=100:gaps.append(dict(a=a['handle'],b=b['handle'],gap_drawing_units=round(gap,2)))
    samples.append(dict(id=item['id'],dimensions=item.get('dimensions'),kind=item.get('kind'),units_header=doc.header.get('$INSUNITS'),
                        source=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),named_devices=devices,observed_row_gaps=gaps,
                        claim='source_geometry_observation_not_manufacturer_minimum_or_approved_placement'))
    print(item['id'],len(devices),flush=True)
result=dict(policy='reference_only_not_approved_training',modern_forms=len(records),legacy_inventory=len(entries),legacy_dxf_inspected=len(samples),
            modern_role_occurrences=dict(counts),common_electrical_blocks=names.most_common(35),modern=records,legacy_samples=samples)
(OUT/'form-study.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
# A contact sheet makes the original layouts reviewable without inventing reconstructed placement.
import cairosvg
from PIL import Image,ImageDraw
ids=['00c63f115a129caf-10E5E99','00c63f115a129caf-10E6F56','00c63f115a129caf-10E72BD','142a10f4b2c12273-108CD58','142a10f4b2c12273-108CD77','142a10f4b2c12273-108CDB5','142a10f4b2c12273-108CDD4','735f6abb77751a37-434']
canvas=Image.new('RGB',(1600,1000),'white');draw=ImageDraw.Draw(canvas)
for index,ident in enumerate(ids):
    svg=modern/ident/'xem_truoc.svg'
    if not svg.is_file():continue
    png=OUT/(ident+'.png')
    try:
        cairosvg.svg2png(url=str(svg),write_to=str(png),output_width=780,output_height=220,background_color='white')
        with Image.open(png) as im:canvas.paste(im.convert('RGB'),((index%2)*800,(index//2)*250+25))
        draw.text(((index%2)*800+10,(index//2)*250+5),ident,fill='black')
    except Exception as exc:draw.text(((index%2)*800+10,(index//2)*250+5),str(exc)[:80],fill='black')
canvas.save(OUT/'source-layout-contact-sheet.jpg')
print(json.dumps({k:result[k] for k in ['modern_forms','legacy_inventory','legacy_dxf_inspected']}))

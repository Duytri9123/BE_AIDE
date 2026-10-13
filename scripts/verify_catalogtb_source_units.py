"""Calibrate two source documents against official anchors, never resize CAD."""
import hashlib,json,re
from pathlib import Path
import ezdxf
from ezdxf import bbox

BASE=Path(__file__).resolve().parents[1]
ROOT=BASE/'data/CatalogTB'
OUT=BASE.parent/'outputs/catalogtb-projection-review'
rows=json.loads((OUT/'evidence.json').read_text(encoding='utf8'))
def save(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def digest(data):return hashlib.sha256(data).hexdigest()
sources={
 'aa426c85a63c42369c7ec4e44b374030232c0d81793325963bb4a82b00aaf35a':[
  (15,420,240,'https://chintglobal.vn/wp-content/uploads/2021/09/nz7-catalog.pdf'),
  (18,140,257,'https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/secondary-power-distribution/mccb/nxm/manual/2104-NXM-MCCB-Manual-2.pdf'),
  (27,210,280,'https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/secondary-power-distribution/mccb/nxm/manual/2104-NXM-MCCB-Manual-2.pdf')],
 'c87e21054c21bd036bd49c7531e3e5c51ef9cf2b9b09e217eaa33280d5bcd591':[
  (176,45,77,'https://www.clipsal.com/products/industrial/tesys/contactor-3p3-no-ac-3-ac-3e-0-to-440v-9a-115vac-50-60hz-coil-lc1d09fe7?itemno=LC1D09FE7'),
  (311,75,130,'https://eshop.se.com/in/mccb-easypact-ezc-ezc100f3100-100a-10ka-3pole-mccb.html')]
}
anchors={}
for source,checks in sources.items():
 anchors[source]=[]
 for number,width,height,url in checks:
    row=next(r for r in rows if r['number']==number)
    p=ROOT/row['profile'];d=json.loads(p.read_text(encoding='utf8'))
    entry=next(v for v in d['cad_don'] if v['id_hinh_goc']==row['view'])
    drawing=p.parent/entry['duong_dan']
    metadata=json.loads((drawing.parent/'thong_tin_cad_chen.json').read_text(encoding='utf8'))
    assert metadata['nguon']['sha256']==source
    doc=ezdxf.readfile(drawing);box=bbox.extents(doc.modelspace(),fast=True)
    assert abs(box.size.x-width)<0.2 and abs(box.size.y-height)<0.2,(number,box.size)
    anchors[source].append({'card':number,'profile':row['profile'],'view':row['view'],
       'cad_dimensions':[box.size.x,box.size.y],'official_mm':[width,height],
       'absolute_tolerance_mm':0.2,'url':url})

report=[]
pattern=rb'(\$INSUNITS\s*\r?\n\s*70\s*\r?\n[ \t]*)(-?\d+)'
for row in rows:
 if row['units']==4:continue
 p=ROOT/row['profile'];d=json.loads(p.read_text(encoding='utf8'))
 entry=next(v for v in d['cad_don'] if v['id_hinh_goc']==row['view'])
 drawing=p.parent/entry['duong_dan']
 metadata_path=drawing.parent/'thong_tin_cad_chen.json'
 metadata=json.loads(metadata_path.read_text(encoding='utf8'))
 origin=metadata.get('nguon') or {};source=origin.get('sha256')
 if source not in anchors:raise ValueError('Uncalibrated source '+str(source))
 scale=origin.get('instance_transform',{}).get('scale')
 assert scale==[1,1,1],(row['number'],scale)
 proof={'status':'source_coordinate_unit_inferred_mm','review_date':'2026-10-11',
  'raw_header_units_code':row['units'],'coordinate_scale_to_mm':1,
  'target_units_code':4,'source_document_sha256':source,'anchors':anchors[source],
  'basis':'Multiple independent official dimension anchors in the same native-coordinate source document; each extracted view has unit instance scale.',
  'geometry_resized':False,'exact_model_dimensions_verified':False,
  'limitation':'Unit calibration does not certify each device envelope, hidden geometry, mounting holes or exact model.'}
 def normalize(path):
    raw=path.read_bytes();matches=list(re.finditer(pattern,raw))
    assert len(matches)==1,path
    match=matches[0];original=int(match[2])
    assert original in (0,1,4),(path,original)
    updated=raw[:match.start(2)]+b'4'+raw[match.end(2):]
    # Header-only replacement: entity bytes and all coordinates stay identical.
    target=path.with_name(path.stem+'_mm.dxf');target.write_bytes(updated)
    assert re.sub(pattern,rb'\g<1>0',raw)==re.sub(pattern,rb'\g<1>0',updated)
    return {'source_file':path.name,'normalized_file':target.name,
       'source_sha256':digest(raw),'normalized_sha256':digest(updated),
       'coordinate_scale_to_mm':1,'target_units_code':4,'raw_units_code':original}
 contract=normalize(drawing)
 native=drawing.parent/'native_preview.json'
 if native.is_file():
    marker=json.loads(native.read_text(encoding='utf8'))
    if marker.get('insertion_outline'):
        outline=(drawing.parent/marker['insertion_outline']).resolve()
        assert outline.parent==drawing.parent.resolve()
        assert digest(drawing.read_bytes())==marker['source_sha256']
        assert digest(outline.read_bytes())==marker['outline_sha256']
        contract['outline']=normalize(outline)
 contract['evidence']=proof
 save(drawing.parent/'verified_units.json',contract)
 entry['unit_verification']=proof
 metadata['unit_verification']=proof
 save(p,d);save(metadata_path,metadata)
 report.append({'profile':row['profile'],'view':row['view'],**contract})
save(OUT/'verified-unit-review.json',{'sources':anchors,'views':report})
print(json.dumps({'normalized_views':len(report),'geometry_scale':1,'original_CAD_preserved':True}))

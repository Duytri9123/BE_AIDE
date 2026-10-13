"""Find small control blocks in the sole original CatalogTB DWG export.

Spatial similarity is candidate evidence only, never a model/brand assertion.
"""
import hashlib,json,logging
from pathlib import Path
import ezdxf
from ezdxf import bbox
logging.getLogger('ezdxf').setLevel(logging.ERROR)
root=Path(__file__).resolve().parents[1]
source=root/'data/CatalogTB/THƯ VIỆN PHỤ KIỆN( Mới nhất).dwg'
scratch=root/'tmp/accessory_source_review/source.dxf'
digest=hashlib.sha256(source.read_bytes()).hexdigest()
assert (scratch.parent/'sha256.txt').read_text()==digest
print('Reading original CatalogTB blocks',flush=True)
doc=ezdxf.readfile(scratch)
candidates=[]; errors=[]; text_hits=[]
cache=bbox.Cache()
for block in doc.blocks:
    texts=[]
    for e in block:
        if e.dxftype() in ('TEXT','MTEXT','ATTDEF','ATTRIB'):
            text=e.plain_text() if e.dxftype()=='MTEXT' else e.dxf.get('text','')
            texts.append(text)
            if any(k in text.upper() for k in ('NCH8','LA63','KG316','CONTACTOR','CHINT','ICT')):
                text_hits.append({'block':block.name,'handle':e.dxf.handle,'text':text})
    if block.name.startswith('*Model_Space') or block.name.startswith('*Paper_Space'): continue
    geometry=[e for e in block if e.dxftype() not in ('TEXT','MTEXT','ATTDEF','ATTRIB','DIMENSION')
              and not e.dxf.get('invisible',0)
              and not doc.layers.get(e.dxf.layer).is_off() and not doc.layers.get(e.dxf.layer).is_frozen()]
    try:
        b=bbox.extents(geometry,cache=cache)
        if b.has_data and 10 <= b.size.x <= 100 and 50 <= b.size.y <= 150:
            candidates.append({'block':block.name,'width':b.size.x,'height':b.size.y,
                               'visible_geometry_entities':len(geometry),'labels':texts,
                               'identity':'unverified_spatial_candidate'})
    except Exception as exc: errors.append({'block':block.name,'error':str(exc)[:200]})
report={'source_sha256':digest,'source_unchanged':hashlib.sha256(source.read_bytes()).hexdigest()==digest,
        'blocks_scanned':len(doc.blocks),'candidates':candidates,'text_hits':text_hits,'errors':errors,
        'modelspace_literals':[{'handle':e.dxf.handle,'text':e.plain_text() if e.dxftype()=='MTEXT' else e.dxf.text}
                              for e in doc.modelspace().query('TEXT MTEXT')
                              if any(k in (e.plain_text() if e.dxftype()=='MTEXT' else e.dxf.text).upper()
                                     for k in ('NCH8','LA63','KG316','CONTACTOR','CHINT','ICT'))]}
folder=root.parent/'outputs/workspace-457-e2e'
(folder/'raw-control-spatial-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'blocks_scanned':report['blocks_scanned'],'spatial_candidates':len(candidates),
                  'text_hits':len(text_hits),'errors':len(errors),'source_unchanged':report['source_unchanged']}),flush=True)

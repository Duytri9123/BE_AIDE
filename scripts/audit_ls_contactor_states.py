"""Check the actual download attributes, metadata and preview for each LS state."""
import hashlib,json
from pathlib import Path
import ezdxf
ROOT=Path(__file__).resolve().parents[1]
jobs=json.loads((ROOT/'tmp/accessory_source_review/ls-rated-state-jobs.json').read_text(encoding='utf8'))
results=[]
for job in jobs:
    folder=(ROOT/'data/CatalogTB'/job['profile']).parent
    cad=folder/'CadDon'/job['view']
    source=folder/'HinhChieu'/job['view']
    doc=ezdxf.readfile(cad/'ban_ve.dxf')
    inserts=list(doc.modelspace().query('INSERT'))
    assert len(inserts)==1,job
    attrs={a.dxf.tag:a.dxf.text for a in inserts[0].attribs}
    assert attrs['TYPE']==job['model'],(job,attrs)
    assert attrs['RATE']==('' if job['rate']=='None' else job['rate']),(job,attrs)
    meta=json.loads((source/'thong_tin.json').read_text(encoding='utf8'))
    assert meta['source_attributes']['TYPE']==attrs['TYPE']
    assert meta['source_attributes'].get('RATE','')==attrs['RATE']
    assert (cad/'xem_truoc.svg').read_bytes()==(source/'xem_truoc.svg').read_bytes()
    preview_doc=ezdxf.readfile(ROOT/'tmp/accessory_source_review'/(job['view']+'-state-preview.dxf'))
    preview_attrs={a.dxf.tag:a.dxf.text for i in preview_doc.modelspace().query('INSERT') for a in i.attribs}
    assert preview_attrs['TYPE']==attrs['TYPE'] and preview_attrs['RATE']==attrs['RATE']
    results.append({'view':job['view'],'state':job['option'],'model':attrs['TYPE'],'rating':attrs['RATE'],
        'dxf_sha256':hashlib.sha256((cad/'ban_ve.dxf').read_bytes()).hexdigest(),
        'preview_sha256':hashlib.sha256((cad/'xem_truoc.svg').read_bytes()).hexdigest()})
fronts=[r for r in results if 'Front' in r['state']]
assert len({r['preview_sha256'] for r in fronts})==len(fronts),'Duplicated front previews'
(ROOT/'docs/library-ls-state-repair.json').write_text(json.dumps({'checked':len(results),'items':results},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Verified',len(results),'CAD states,',len(fronts),'distinct front previews')

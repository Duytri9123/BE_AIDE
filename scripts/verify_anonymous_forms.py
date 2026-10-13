"""Verify published mechanical forms and synchronize anonymous reference labels."""
import json
from pathlib import Path
import ezdxf
from ezdxf import bbox
ROOT=Path(__file__).resolve().parents[1]/'data/CatalogTB/Form tủ'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
d=read(ROOT/'catalog.json');results=[]
assert all('mechanical_cleaning' in r for r in d['shells']), 'Cleanup still running'
for r in d['shells']:
 folder=ROOT/'Mau'/r['id'];doc=ezdxf.readfile(folder/'ban_ve.dxf')
 if r.get('cad_scope')=='source_shell_views_with_original_dimensions_and_colors':
  assert not list(doc.modelspace().query('HATCH REGION BODY 3DSOLID'))
 else:assert not list(doc.modelspace().query('INSERT TEXT MTEXT ATTRIB ATTDEF DIMENSION HATCH REGION BODY 3DSOLID'))
 ext=bbox.extents(doc.modelspace(),fast=True)
 planar=not ext.has_data or (abs(ext.extmin.z)<1e-7 and abs(ext.extmax.z)<1e-7)
 r['mechanical_cleaning']['flat_modelspace']=planar
 # Planarity and label counts do not verify source face completeness or cleanup.
 r['mechanical_cleaning']['needs_review']=True
 r['auto_select']=False
 for filename in ('bo_tri_goc.json','tham_chieu_dong_goc.json'):
  p=folder/filename
  if p.exists():
   reference=read(p);reference['cabinet_name']=r['name'];reference.pop('source_file',None)
   reference['reference_only']=True;save(p,reference)
 save(folder/'thong_tin.json',r)
 results.append({'id':r['id'],'name':r['name'],'planar':planar,'entities':len(doc.modelspace()),'views':len(r.get('faces',[])),'needs_review':r['mechanical_cleaning']['needs_review']})
save(ROOT/'catalog.json',d);save(ROOT/'kiem_tra_form_co_khi.json',results)
print('Verified',len(results),'forms;',sum(r['views'] for r in results),'view labels;',sum(not r['planar'] for r in results),'non-planar;',sum(r['needs_review'] for r in results),'require review')

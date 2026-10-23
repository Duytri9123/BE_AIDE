"""Review previously unresolved CHINT drawings against source geometry/text, with backups."""
import json,hashlib,sqlite3,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from ls_native_writer import ROOT,CAT
OUT=ROOT/'docs/ls-chint-face-review-2026-10-21'
DECISIONS={
 'SOURCE-0ba9f4b5eac3b2ad':('Mặt bên · đầu tròn','PUSHBUTTON','Nút nhấn CHINT NP2 · NO · đầu tròn','NO'),
 'SOURCE-1fe641d7c068577b':('Mặt bên · đầu tròn','PUSHBUTTON','Nút nhấn CHINT NP2 · NC · đầu tròn','NC'),
 'SOURCE-ac081eb996b2eefe':('Mặt bên · đầu nhô','PUSHBUTTON','Nút nhấn CHINT NP2 · NO · đầu nhô','NO'),
 'SOURCE-d40f9833bc813ad2':('Mặt bên · đầu nhô','PUSHBUTTON','Nút nhấn CHINT NP2 · NC · đầu nhô','NC'),
 'SOURCE-a37c936f81abba26':('Mặt trước','FUSEASSEMBLY','Bộ cầu chì CHINT RT36-00 · 160 A',None),
 'SOURCE-d99fbb3779c7d135':('Mặt trước · bảng nhiều thiết bị','ASSEMBLY_REFERENCE','Bảng thiết bị điều khiển CHINT NP2 · CAD tham khảo',None),
}

def main():
 rows=json.loads((OUT/'unresolved-before.json').read_text(encoding='utf8'));review=[]
 with sqlite3.connect(CAT/'_agent_index/equipment_catalog.sqlite') as db:
  for row in rows:
   p=CAT/row['profile'];d=json.loads(p.read_text(encoding='utf8'));v=next(v for v in d['cad_don'] if v['id_hinh_goc']==row['view']['id_hinh_goc']);ident=v['id_hinh_goc']
   if ident not in DECISIONS:raise ValueError('Unreviewed face requires an explicit decision: '+ident)
   drawing=p.parent/v['duong_dan'];doc=ezdxf.readfile(drawing);assert not doc.audit().errors
   texts='\n'.join(e.dxf.text if e.dxftype()=='TEXT' else e.plain_text() for e in doc.modelspace().query('TEXT MTEXT'))
   label,kind,name,contact=DECISIONS[ident]
   if contact:assert '('+contact+')' in texts and 'NP2' in texts
   elif kind=='FUSEASSEMBLY':assert 'RT36-00' in texts and '160A' in texts
   else:assert all(t in texts for t in ['RUN','STOP','FAULT','AUTO','MAN'])
   backup=OUT/'before'/row['profile'];backup.parent.mkdir(parents=True,exist_ok=True)
   if not backup.exists():backup.write_bytes(p.read_bytes())
   evidence={'status':'orientation_identified','method':'Visual inspection of complete source projection and source DXF text; checked against NP2/RT36 manufacturer family drawings. Side views show contact block, thread, bezel and head on the same assembly. RT36 shows cartridge and base from the labelled front. NP2 panel shows several independent front controls, not a single device.','source_dxf_sha256':hashlib.sha256(drawing.read_bytes()).hexdigest(),'previous_label':row['view']['huong_nhin'],'reviewed_label':label,'checked_at':'2026-10-21','ordering_code_verified':False}
   v.update(huong_nhin=label,nhan_hien_thi=label,orientation_review=evidence)
   # Orientation recognition does not certify the manufacturing geometry/SKU.
   v['bo_tri_trong_tu']={'cho_phep_chen':False,'huong_dan':'CAD tham khảo; xác nhận cấu hình và bao hình trước bố trí.'}
   d.update(ten_san_pham=name,ban_chat=kind,auto_select=False,needs_review=True)
   d['nhan_dien_ai'].update(loai_thiet_bi_code=kind,source_component_type=kind,fabrication_ready=False)
   if contact:d['thong_so'].update(tiep_diem_tren_cad=contact,head_shape_reference=label.split(' · ')[-1])
   if kind=='ASSEMBLY_REFERENCE':d['source_catalog_review']['contains_multiple_components']=True;d['thong_so']['Phạm vi bản vẽ']='Bảng gồm nhiều thiết bị; không phải một nút nhấn đơn'
   d['tu_khoa_tim_kiem']=['CHINT','NP2' if kind!='FUSEASSEMBLY' else 'RT36-00',kind,name]
   d['cad_chen_tu']={k:v[k] for k in ['id_hinh_goc','huong_nhin','duong_dan']}
   p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
   cid='TB-'+hashlib.sha1(row['profile'].encode()).hexdigest()[:16];record=db.execute('SELECT record_json FROM equipment WHERE catalog_id=?',(cid,)).fetchone()
   if record:
    r=json.loads(record[0]);r.update(display_name=name,category=kind,auto_select=False)
    for view in r.get('cad',{}).get('views',[]):
     if view['id']==ident:view.update(name=label,state=label,placement=v['bo_tri_trong_tu'])
    db.execute('UPDATE equipment SET category=?,display_name=?,record_json=? WHERE catalog_id=?',(kind,name,json.dumps(r,ensure_ascii=False),cid));db.execute('UPDATE equipment_fts SET category=?,display_name=? WHERE catalog_id=?',(kind,name,cid))
   review.append({'profile':row['profile'],'id':ident,'label':label,'type':kind,'evidence':evidence})
 (OUT/'resolved-views.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf8');print('Resolved',len(review),'views; no geometry deleted')
if __name__=='__main__':main()

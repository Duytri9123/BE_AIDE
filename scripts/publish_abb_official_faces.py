"""Attach audited manufacturer faces to ABB profiles, preserving source variants."""
import json
import os
import shutil
import sqlite3
import hashlib
import ezdxf
from ezdxf.addons.drawing import Frontend,RenderContext,svg,layout
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw
from import_abb_official_faces import ROOT,SOURCES


def main():
 report=json.loads((ROOT.parents[1]/'docs/abb-official-faces-2026-10-20.json').read_text(encoding='utf8'))
 for family,(uid,_) in SOURCES.items():
  for poles in ('3P','4P'):
   path=ROOT/'ABB/ThietBi'/f'{family}_{poles}'/'thong_tin_thiet_bi.json'
   profile=json.loads(path.read_text(encoding='utf8'))
   profile['cad_don']=[v for v in profile['cad_don'] if not str(v['id_hinh_goc']).startswith('ABB-OFFICIAL-')]
   for variant,face in ((poles,'Mặt trước'),('side','Mặt bên')):
    item=next(r for r in report if r['family']==family and r['variant']==variant)
    folder=ROOT/item['directory'];evidence=json.loads((folder/'evidence.json').read_text(encoding='utf8'))
    geometry={'hinh_hoc_lap_dat':{'don_vi':'mm','bao_hinh_mm':{'min_x':0,'min_y':0,'max_x':evidence['width_mm'],'max_y':evidence['height_mm']}},
              'source':evidence,'mounting_holes_verified':False}
    (folder/'thong_tin_cad_chen.json').write_text(json.dumps(geometry,ensure_ascii=False,indent=2),encoding='utf8')
    identity=f'ABB-OFFICIAL-{family}-{poles}-{variant}-FIXED-F'
    destination=path.parent/'CadDon'/identity;destination.mkdir(parents=True,exist_ok=True)
    for filename in ('ban_ve.dxf','thong_tin_cad_chen.json','evidence.json'):
     shutil.copy2(folder/filename,destination/filename)
    preview=folder/'xem_truoc.svg'
    if not preview.exists():
     doc=ezdxf.readfile(folder/'ban_ve.dxf');backend=svg.SVGBackend()
     Frontend(RenderContext(doc),backend).draw_layout(doc.modelspace(),finalize=True)
     preview.write_text(backend.get_string(layout.Page(0,0,layout.Units.mm)),encoding='utf8')
    shutil.copy2(preview,destination/'xem_truoc.svg')
    profile['cad_don'].append({'id_hinh_goc':identity,'huong_nhin':face,
      'nhan_hien_thi':f'ABB · MCCB · {family} · {poles} · Cố định F · {face}',
      'duong_dan':Path(os.path.relpath(destination/'ban_ve.dxf',path.parent)).as_posix(),
      'bien_the_cad':'abb_official_fixed_F_20261020','vai_tro_cad':'device_view',
      'unit_verification':evidence,'bo_tri_trong_tu':{'cho_phep_chen':True,
      'huong_dan':'Bao hình CAD hãng có đầu nối/vách ngăn theo hình nguồn; đối chiếu phụ kiện và mã điện trước đặt hàng.'}})
   profile['cac_hinh_cad']=list(dict.fromkeys(profile.get('cac_hinh_cad',[])+[v['id_hinh_goc'] for v in profile['cad_don']]))
   profile.setdefault('quy_tac_dung_chung_cad',{})['new_faces_imported']=True
   profile['nguon_tham_khao']=list(dict.fromkeys(profile.get('nguon_tham_khao',[])+[next(r['source_url'] for r in report if r['family']==family)]))
   path.write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
   cid='TB-'+hashlib.sha1(path.relative_to(ROOT).as_posix().encode()).hexdigest()[:16]
   with sqlite3.connect(ROOT/'_agent_index/equipment_catalog.sqlite') as db:
    row=db.execute('SELECT record_json FROM equipment WHERE catalog_id=?',(cid,)).fetchone()
    if not row:raise ValueError('Missing indexed profile: '+cid)
    record=json.loads(row[0]);views=[v for v in record['cad']['views'] if not str(v.get('id','')).startswith('ABB-OFFICIAL-')]
    for v in profile['cad_don']:
     if not v['id_hinh_goc'].startswith('ABB-OFFICIAL-'):continue
     folder=(path.parent/v['duong_dan']).parent
     relative='catalogtb/'+folder.relative_to(ROOT).as_posix()
     views.append({'id':v['id_hinh_goc'],'name':v['nhan_hien_thi'],'state':v['huong_nhin'],
      'preview':{'path':relative+'/xem_truoc.svg'},'dxf':{'path':relative+'/ban_ve.dxf'},'placement':v['bo_tri_trong_tu']})
    record['cad']['views']=views
    db.execute('UPDATE equipment SET record_json=? WHERE catalog_id=?',(json.dumps(record,ensure_ascii=False),cid))
 canvas=Image.new('RGB',(1200,1200),'#ffffff');draw=ImageDraw.Draw(canvas)
 for index,item in enumerate(report):
  photo=Image.open(ROOT/item['directory']/'preview.png').convert('RGB');photo=ImageOps.contain(photo,(270,340))
  x=(index%4)*300+(300-photo.width)//2;y=(index//4)*400+35
  canvas.paste(photo,(x,y));draw.text(((index%4)*300+12,(index//4)*400+10),f"ABB {item['family']} {item['variant']} Fixed F",fill='black')
 output=ROOT.parents[1]/'docs/abb-official-faces-2026-10-20.png';canvas.save(output)
 print('Published 16 profile views from 12 manufacturer projections')


if __name__=='__main__':main()

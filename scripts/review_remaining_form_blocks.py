"""Audit published blocks against original equipment occurrences and hardware names."""
import ast,json,re,logging
from pathlib import Path
import ezdxf
from ezdxf import dynblkhelper
from project_form_rejections import norm
from extract_project_helpers import ROOT,OUT,save
tree=ast.parse((ROOT/'BE_AIDE/scripts/restore_complete_e_side_geometry.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef))],type_ignores=[]),'helpers','exec'))
logging.getLogger('ezdxf').setLevel(logging.ERROR)
hardware=re.compile(r'HL\d|MS(?:722|303|308|325|406)|AB301|KHOA|LOCK|HINGE|LIFT|HM10|TAI|MOC')
electrical=re.compile(r'ME4[01]|MCCB|MCB|ACB|RCBO|RCCB|CONTACTOR|ATS |ABN|EZC|CAU CHI|PNE.BAR|VTPK|COS [0-9]|THANH U|THANH DOC|XA SAU|SU KEP|SU PHIP|CAU TIEP DIA|O CAM CN|DEN BAO')
data=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));report=[]
for r in data['shells']:
 folder=OUT/'Mau'/r['id'];original=json.loads((folder/'bo_tri_goc.json').read_text(encoding='utf-8'))
 occurrences={(round(e['insertion_point_source'][0],3),round(e['insertion_point_source'][1],3)):e for e in original['layout_occurrences']};side_positions={(round(e['insertion_point_source'][0],3),round(e['insertion_point_source'][1],3)) for e in original['layout_occurrences'] if e.get('source_handle') in {a['source_handle'] for a in r.get('side_view_source_blocks',[])}}
 changes={};unknown=[]
 for fn in ('ban_ve.dxf','ban_ve_co_khung_goc.dxf'):
  doc=ezdxf.readfile(folder/fn);removed=[]
  for e in list(doc.modelspace().query('INSERT')):
   definition=dynblkhelper.get_dynamic_block_definition(e);name=definition.name if definition else e.dxf.name;n=norm(name);pos=(round(e.dxf.insert.x,3),round(e.dxf.insert.y,3));source=occurrences.get(pos);role=source.get('role') if source else None
   if hardware.search(n) or name.startswith('_Open') or 'STANDARD' in n or 'THONG SO' in n:continue
   if electrical.search(n) or role in ('device','electrical_accessory','terminal'):
    removed.append({'output_handle':e.dxf.handle,'name':name,'source_occurrence':source});doc.modelspace().delete_entity(e)
   elif fn=='ban_ve.dxf':unknown.append({'name':name,'position':[e.dxf.insert.x,e.dxf.insert.y],'source_occurrence':source,'retained_basis':'source_side_block' if pos in side_positions else 'unidentified_requires_source_review'})
  if removed:
   doc.saveas(folder/fn)
   if fn=='ban_ve_co_khung_goc.dxf':render(doc,folder/'xem_truoc.svg')
  changes[fn]=removed
 audit={'id':r['id'],'removed_identified_electrical_blocks':changes,'retained_unidentified_blocks':unknown,'complete_semantic_review':False};r['remaining_block_review']=audit;r['mechanical_cleaning']['needs_review']=True;save(folder/'thong_tin.json',r);report.append(audit)
save(OUT/'catalog.json',data);save(OUT/'kiem_tra_thiet_bi_con_sot.json',report)
print('Reviewed',len(report),'forms; removed',sum(len(r['removed_identified_electrical_blocks']['ban_ve.dxf']) for r in report),'identified blocks; remaining unidentified',sum(len(r['retained_unidentified_blocks']) for r in report))

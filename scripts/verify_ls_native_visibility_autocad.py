import json,subprocess,re,sys,time
from pathlib import Path
import pythoncom,win32com.client
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root));report=root/'docs/ls-all-cad-2026-10-24/native-visibility-batch.json';rows=json.loads(report.read_text(encoding='utf8'))['items'];out=root/'tmp/ls-visibility/validated';out.mkdir(exist_ok=True)
pythoncom.CoInitialize();host=win32com.client.GetActiveObject('AutoCAD.Application');results=[]
for row in rows:
 path=Path(row['file']);dst=out/(path.stem+'.dwg');script=out/(path.stem+'.scr');script.write_text('FILEDIA\n0\n_.AUDIT\n_Yes\n_.-WBLOCK\n'+dst.as_posix()+'\n*\n_.QUIT\n_Yes\n',encoding='ascii');log=out/(path.stem+'.log')
 if not dst.exists():
  with log.open('wb') as stream:subprocess.run([r'C:\Program Files\Autodesk\AutoCAD 2022\accoreconsole.exe','/i',str(path),'/s',str(script),'/l','en-US'],stdout=stream,stderr=subprocess.STDOUT,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
 text=log.read_text(encoding='utf-16-le',errors='replace');assert 'Total errors found 0 fixed 0' in text,(path,'AutoCAD audit failed')
 db=host.GetInterfaceObject('ObjectDBX.AxDbDocument.24');db.Open(str(dst));ref=db.ModelSpace.Item(0);assert ref.IsDynamicBlock
 prop=next(p for p in ref.GetDynamicBlockProperties() if p.PropertyName=='CAD_FACE');states=list(prop.AllowedValues);assert len(states)==row['faces'],(path,states,row['faces'])
 for state in states:
  prop.Value=state;assert prop.Value==state
  block=db.Blocks.Item(ref.Name);members=list(block);assert len(members)==len(states);assert sum(bool(e.Visible) for e in members)==1,(path,state,'Faces overlap')
 results.append({'catalog_id':row['catalog_id'],'variant_id':row['variant_id'],'states':states,'autocad_audit':'0 errors / 0 fixes','all_states_switched':True,'one_face_visible_each_state':True});print('VERIFIED',len(results),'/',len(rows),row['catalog_id'],len(states),flush=True);db=None
 (root/'docs/ls-all-cad-2026-10-24/autocad-batch-verification.json').write_text(json.dumps({'groups':len(results),'faces':sum(len(x['states']) for x in results),'items':results},ensure_ascii=False,indent=2),encoding='utf8')
print('ALL PASSED',len(results),flush=True)


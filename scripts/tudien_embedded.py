from build_tudien_library import *
import zipfile,io
from PIL import Image,ImageDraw
media={};oles=[]
for p in SOURCE.glob('*.xlsx'):
 sid=hashlib.sha256(p.read_bytes()).hexdigest()[:16]
 with zipfile.ZipFile(p) as z:
  for n in z.namelist():
   if not n.startswith('xl/media/'):continue
   data=z.read(n);mid=hashlib.sha256(data).hexdigest()[:20];dest=OUT/'nguon/embedded_media'/(mid+Path(n).suffix)
   dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
   if mid not in media:media[mid]={'id':mid,'path':str(dest.relative_to(OUT)).replace('\\','/'),'sources':[],'status':'extracted_pending_visual_review'}
   media[mid]['sources'].append({'source_id':sid,'zip_path':n})
save(OUT/'embedded_media.json',list(media.values()))
thumbs=[]
for i,m in enumerate(media.values()):
 try:
  im=Image.open(OUT/m['path']).convert('RGB');im.thumbnail((460,300));tile=Image.new('RGB',(480,340),'white');tile.paste(im,((480-im.width)//2,25));ImageDraw.Draw(tile).text((8,8),str(i)+' '+m['id'],fill='black');thumbs.append(tile)
 except Exception as e:m['preview_error']=str(e)
for start in range(0,len(thumbs),12):
 grid=Image.new('RGB',(1920,1020),'#ddd')
 for j,t in enumerate(thumbs[start:start+12]):grid.paste(t,((j%4)*480,(j//4)*340))
 grid.save(ROOT.parent/'tmp'/f'tudien_embedded_{start//12}.png')
for p in (OUT/'nguon').glob('*/drawing.dxf'):
 doc=ezdxf.readfile(p)
 for ent in doc.entitydb.values():
  if ent.dxftype()!='OLE2FRAME':continue
  data=ent.binary_data();oid=hashlib.sha256(data).hexdigest()[:20];dest=OUT/'nguon/embedded_ole'/f'{oid}.bin';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
  rec={'source_id':p.parent.name,'handle':ent.dxf.handle,'id':oid,'bytes':len(data),'status':'binary_preserved'}
  offset=data.find(bytes.fromhex('d0cf11e0a1b11ae1'))
  if offset>=0:
   try:
    wb=xlrd.open_workbook(file_contents=data[offset:]);sheets=[{'sheet':s.name,'rows':[{'row':r+1,'values':s.row_values(r)} for r in range(s.nrows)]} for s in wb.sheets()];save(dest.with_suffix('.json'),sheets);rec['status']='excel_rows_extracted';rec['sheets']=len(sheets)
   except Exception as e:rec['error']=str(e)
  oles.append(rec)
 save(OUT/'embedded_ole.json',oles);print(p.parent.name,flush=True)
save(OUT/'embedded_media.json',list(media.values()));save(OUT/'embedded_ole.json',oles)
print('media',len(media),'ole',len(oles),collections.Counter(o['status'] for o in oles),flush=True)

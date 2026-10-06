from build_tudien_library import *
import olefile,io,zipfile
decoded=[]
for p in (OUT/'nguon/embedded_ole').glob('*.bin'):
 rec={'id':p.stem};data=p.read_bytes();offset=data.find(bytes.fromhex('d0cf11e0a1b11ae1'))
 try:
  ole=olefile.OleFileIO(io.BytesIO(data[offset:]));rec['streams']=ole.listdir();sheets=[]
  if ole.exists('Package'):
   package=ole.openstream('Package').read();p.with_suffix('.xlsx').write_bytes(package)
   w=openpyxl.load_workbook(io.BytesIO(package),data_only=False);v=openpyxl.load_workbook(io.BytesIO(package),data_only=True)
   for s in w:
    rows=[]
    for row in s:
     cells=[{'column':c.column,'value':c.value,'cached':v[s.title].cell(c.row,c.column).value} for c in row if c.value is not None]
     if cells:rows.append({'row':row[0].row,'cells':cells})
    sheets.append({'sheet':s.title,'rows':rows})
  elif ole.exists('Workbook') or ole.exists('Book'):
   w=xlrd.open_workbook(file_contents=data[offset:]);sheets=[{'sheet':s.name,'rows':[{'row':r+1,'cells':[{'column':c+1,'value':s.cell_value(r,c)} for c in range(s.ncols) if s.cell_value(r,c)!='']} for r in range(s.nrows)]} for s in w.sheets()]
  if sheets:save(p.with_suffix('.json'),sheets);rec.update(status='workbook_extracted',sheets=len(sheets),rows=sum(len(s['rows']) for s in sheets))
  else:rec['status']='non_workbook_ole'
 except Exception as e:rec.update(status='decode_error',error=str(e))
 decoded.append(rec)
save(OUT/'embedded_ole_decoded.json',decoded);print(collections.Counter(x['status'] for x in decoded))

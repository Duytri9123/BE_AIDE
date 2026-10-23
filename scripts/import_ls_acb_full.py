"""Extract three actual ACB projections, keyed by frame/poles/mounting/terminal orientation."""
import json,re,hashlib,collections,sys
from pathlib import Path
import ezdxf
from ezdxf import bbox,disassemble
from ls_native_writer import CAT,ROOT,write_profile,price_option
PRICES=[r for r in json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'] if r.get('category')=='ACB' and str(r.get('brand','')).lower() in ['ls','ls electric']]
def groups(intervals):
 result=[]
 for a,b in sorted(intervals):
  if not result or a>result[-1][1]+2:result.append([a,b])
  else:result[-1][1]=max(result[-1][1],b)
 return result

def main():
 report=[]
 for path in sorted((CAT/'LS/NguonBenNgoai').glob('*/source.json')):
  ev=json.loads(path.read_text(encoding='utf8'));name=ev.get('file',{}).get('df_name','')
  if 'ACB' not in name or '2D CAD' not in name or not (path.parent/'source.dxf').exists():continue
  match=re.search(r'(?:06~16D|20~32E|40E|40~50F|63G)([34])',name)
  if not match:continue
  poles=match[1];frame=re.search(r'(06~16D|20~32E|40E|40~50F|63G)',name)[1];mount='WITHDRAW' if 'WITHDRAW' in name.upper() else 'FIXED';terminal='V' if re.search(r'_V_',name) else 'H';family='ACB-'+frame.replace('~','-')+'-'+poles+'P-'+terminal+'-'+mount
  if '--withdraw-only' in sys.argv and mount!='WITHDRAW':continue
  dxf=path.parent/'source.dxf';doc=ezdxf.readfile(dxf);assert doc.units==4
  geometry=[]
  for src in doc.modelspace():
   if src.dxftype() in {'DIMENSION','ACAD_TABLE','LEADER','MLEADER'}:continue
   for e in disassemble.recursive_decompose([src]):
    if e.dxftype() not in {'LINE','ARC','CIRCLE','SPLINE','ELLIPSE','LWPOLYLINE','POLYLINE'}:continue
    color=e.dxf.color;color=7 if color==0 else (doc.layers.get(e.dxf.layer).dxf.color if color==256 else color)
    if color not in ({7,4,5,2} if mount=='WITHDRAW' else {7}):continue
    if e.dxf.layer.lower()=='3_all_axes':continue
    b=bbox.extents([e])
    if b.has_data:geometry.append((e,b))
  xbands=[g for g in groups([(b.extmin.x,b.extmax.x) for e,b in geometry]) if g[1]-g[0]>180]
  if len(xbands)!=2:report.append({'file':path.parent.name,'error':'Unclear X bands','bands':xbands});continue
  first,second=xbands
  side_geometry=[(e,b) for e,b in geometry if b.extmin.x>=second[0]-.01 and b.extmax.x<=second[1]+.01]
  ybands=groups([(b.extmin.y,b.extmax.y) for e,b in side_geometry]);body=max(ybands,key=lambda g:g[1]-g[0])
  if body[1]-body[0]<200:report.append({'file':path.parent.name,'error':'Missing body projection'});continue
  def crop(xband,yband):return [e for e,b in geometry if b.extmin.x>=xband[0]-.01 and b.extmax.x<=xband[1]+.01 and b.extmin.y>=yband[0]-.01 and b.extmax.y<=yband[1]+.01]
  front=crop(first,body);side=crop(second,body);top=[e for e,b in geometry if b.extmin.x>=first[0]-.01 and b.extmax.x<=first[1]+.01 and b.extmin.y>body[1]+5]
  bf,bs,bt=[bbox.extents(es) for es in [front,side,top]]
  if not bt.has_data or abs(bf.size.y-bs.size.y)>.1 or abs(bf.size.x-bt.size.x)>8:
   report.append({'file':path.parent.name,'error':'Projection envelope mismatch','front':tuple(bf.size),'side':tuple(bs.size),'top':tuple(bt.size)});continue
  options=[];models=[]
  for row in PRICES:
   m=re.match(r'^(AN|AS|AH|AV|AW)-(\d{2})([DEFG])([34])-\d{2}([HVA])',row['sku'])
   if not m or m[4]!=poles:continue
   n=int(m[2]);valid={'06~16D':m[3]=='D' and 6<=n<=16,'20~32E':m[3]=='E' and 20<=n<=32,'40E':m[3]=='E' and n==40,'40~50F':m[3]=='F' and 40<=n<=50,'63G':m[3]=='G' and n==63}[frame]
   group=str(row.get('group') or '').upper();requested_mount='WITHDRAW' if 'DRAW-OUT' in group else 'FIXED'
   if not valid or requested_mount!=mount:continue
   if mount=='FIXED' and m[5]!=terminal:continue
   options.append(price_option(row));models.append(f'{m[1]}-{m[2]}{m[3]}{m[4]}')
  if not options:report.append({'file':path.parent.name,'error':'No pricebook configuration'});continue
  ev.update(source_dxf_sha256=hashlib.sha256(dxf.read_bytes()).hexdigest(),unit_evidence='Native supplier INSUNITS=4 (mm)',projection_method='White supplier geometry; separate native front/side/top bands, dimensions excluded',source_frame=frame,mounting=mount,terminal_orientation=terminal)
  name=f'LS · ACB · {frame} · {poles}P · '+('Rút kéo' if mount=='WITHDRAW' else 'Cố định')+' · Đầu nối '+terminal
  write_profile(family,name,'ACB',list(dict.fromkeys(models)),poles+'P',options,[('FRONT','Mặt trước',front),('SIDE','Mặt bên',side),('TOP','Mặt trên',top)],ev,{'Kiểu lắp':'Rút kéo' if mount=='WITHDRAW' else 'Cố định','Hướng đầu nối':terminal})
  report.append({'file':path.parent.name,'family':family,'price_rows':len(options),'status':'imported'})
 (ROOT/'docs/ls-acb-full-import-2026-10-20.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report),flush=True)
if __name__=='__main__':main()

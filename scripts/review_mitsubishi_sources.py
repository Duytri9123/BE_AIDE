"""Render native projected directions for manual orientation review."""
import json,sys
from pathlib import Path
import fitz
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/CatalogTB/Mitsubishi/NguonBenNgoai/PRIMARY-20261022'
manifest=sys.argv[1] if len(sys.argv)>1 else 'downloads.json'
OUT=ROOT/('tmp/mitsu-'+Path(manifest).stem+'-review' if manifest!='downloads.json' else 'tmp/mitsu-review');OUT.mkdir(exist_ok=True)
doc=fitz.open(SRC/'ws-v-catalogue.pdf')
hits=[(i+1,p.get_text()) for i,p in enumerate(doc) if 'NV63' in p.get_text() and 'M5' in p.get_text() and 'M8' in p.get_text()]
(OUT/'terminal-evidence.txt').write_text('\n'.join(str(i)+'\n'+t for i,t in hits),encoding='utf8')
print('terminal pages',[i for i,t in hits])
items=sorted(json.loads((SRC/manifest).read_text())['downloaded'],key=lambda x:x['file_name'])
codes=['FRONT','REAR','SIDE-L','SIDE','TOP','BOTTOM']
for start in range(0,len(items),8):
 sheet=Image.new('RGB',(1200,8*155),'white');draw=ImageDraw.Draw(sheet)
 for k,item in enumerate(items[start:start+8]):
  folder=SRC/Path(item['file_name']).stem
  draw.text((5,k*155+2),f"{start+k} {folder.name}",fill='black')
  for col,code in enumerate(codes):
   f=folder/(code+'.png')
   if not f.exists():f=folder/('hlr-poly-all-'+code+'.png')
   im=Image.open(f).convert('RGB');im.thumbnail((190,125))
   sheet.paste(im,(col*200+(190-im.width)//2,k*155+28))
   draw.text((col*200+5,k*155+16),code,fill='black')
 sheet.save(OUT/f'sheet-{start:03}.png')
print('sheets',len(list(OUT.glob('sheet-*.png'))))

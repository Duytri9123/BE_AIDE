"""Contact sheets for the source items that originally had no preview."""
import json,re
from pathlib import Path
from xml.etree import ElementTree as ET
import pymupdf
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB';OUT=ROOT/'outputs/source-630-review'

def main():
    original=json.loads((OUT/'inventory.json').read_text(encoding='utf8'))
    processed=json.loads((ROOT/'docs/source-630-catalog-processing.json').read_text(encoding='utf8'))['items']
    index={r['index']:r for r in processed};rows=[]
    for r in original:
        if r.get('preview_path') or not index[r['index']].get('profile'):continue
        p=CAT/index[r['index']]['profile'];d=json.loads(p.read_text(encoding='utf8'));v=d['cad_don'][0]
        rows.append((r['index'],d['ten_san_pham'],(p.parent/v['duong_dan']).parent/'xem_truoc.svg'))
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
    for start in range(0,len(rows),50):
        sheet=Image.new('RGB',(1600,1800),'white');draw=ImageDraw.Draw(sheet)
        for i,(number,name,path) in enumerate(rows[start:start+50]):
            x=i%5*320;y=i//5*180
            draw.text((x+3,y+2),f'#{number} {name[:34]}',font=font,fill='black')
            svg=ET.fromstring(path.read_bytes())
            rules={n:dict(p.strip().split(':',1) for p in body.split(';') if ':' in p)
                   for style in svg.iter('{http://www.w3.org/2000/svg}style')
                   for n,body in re.findall(r'\.([\w-]+)\s*\{([^}]+)\}',style.text or '')}
            for e in svg.iter():
                for c in e.attrib.get('class','').split():
                    for k,v in rules.get(c,{}).items():e.set(k.strip(),v.strip())
            doc=pymupdf.open(stream=ET.tostring(svg),filetype='svg')
            pdf=pymupdf.open(stream=doc.convert_to_pdf(),filetype='pdf');page=pdf[0]
            scale=min(310/page.rect.width,150/page.rect.height)
            pix=page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False)
            photo=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
            sheet.paste(photo,(x+(320-pix.width)//2,y+25))
        sheet.save(OUT/f'added-previews-{start//50+1}.png')
    print('Rendered',len(rows),'previously missing source previews')

if __name__=='__main__':main()

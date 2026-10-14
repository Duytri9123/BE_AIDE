"""Render a contact sheet of unknown priority CADs for visual identity review."""
import json
import re
import argparse
from pathlib import Path
from urllib.parse import unquote,urlsplit
from xml.etree import ElementTree as ET
import pymupdf
from PIL import Image,ImageDraw,ImageFont
from app.services.catalogtb_browser import browser_data
from app.services.library_review_scope import exact_price_required
from app.services.equipment_library import asset_bytes
from app.api.v1.endpoints.equipment_library import _cad_view_file

ROOT=Path(__file__).resolve().parents[1]


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--additional',action='store_true')
    parser.add_argument('--source-research',action='store_true');args=parser.parse_args()
    out=ROOT/'outputs/folder-web-review';out.mkdir(parents=True,exist_ok=True)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
    devices=[d for d in browser_data()['items'] if d['brand_identification_status']=='unknown' and exact_price_required(d)]
    records=[(d,v) for d in devices for v in (d['views'][1:] if args.additional else d['views'][:1])]
    prefix='unknown-additional' if args.additional else 'unknown-priority'
    if args.source_research:
        research=json.loads((ROOT/'docs/library-source-model-research.json').read_text(encoding='utf8'))
        wanted={r['id'] for r in research['items'] if r['status']!='source_model_documented'}
        pinned=ROOT/'docs/library-source-face-index.json'
        if pinned.is_file():
            wanted={r['id'] for r in json.loads(pinned.read_text(encoding='utf8'))}
        devices=[d for d in browser_data()['items'] if d['id'] in wanted]
        records=[(d,v) for d in devices for v in d['views']]
        prefix='source-unresolved-all-faces'
    for start in range(0,len(records),15):
        sheet=Image.new('RGB',(1200,1500),'white');draw=ImageDraw.Draw(sheet)
        for index,(d,view) in enumerate(records[start:start+15]):
            x=(index%3)*400;y=(index//3)*300
            parts=urlsplit(view['preview']).path.strip('/').split('/')
            svg=ET.fromstring(asset_bytes(_cad_view_file(unquote(parts[1]),unquote(parts[3]),'preview')))
            # MuPDF's SVG reader ignores CSS classes; inline the original declarations for faithful rendering.
            rules={name:dict(part.strip().split(':',1) for part in body.split(';') if ':' in part)
                   for style in svg.iter('{http://www.w3.org/2000/svg}style')
                   for name,body in re.findall(r'\.([\w-]+)\s*\{([^}]+)\}',style.text or '')}
            for node in svg.iter():
                for name in node.attrib.get('class','').split():
                    for key,value in rules.get(name,{}).items():node.set(key.strip(),value.strip())
            bounds=svg.attrib['viewBox'].split()
            bg=ET.Element('{http://www.w3.org/2000/svg}rect',{'x':bounds[0],'y':bounds[1],'width':bounds[2],'height':bounds[3],'fill':'#212930'})
            svg.insert(0,bg)
            doc=pymupdf.open(stream=ET.tostring(svg),filetype='svg')
            pdf=pymupdf.open(stream=doc.convert_to_pdf(),filetype='pdf');page=pdf[0]
            scale=min(380/page.rect.width,245/page.rect.height)
            pix=page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False)
            photo=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
            sheet.paste(photo,(x+(400-photo.width)//2,y+5))
            draw.text((x+8,y+253),f'{start+index+1}. {d["id"]}',font=font,fill='black')
            draw.text((x+8,y+274),d['display'][:32]+' · '+view.get('label','')[:14],font=font,fill='black')
        sheet.save(out/f'{prefix}-{start//15+1}.png')
    (out/f'{prefix}-index.json').write_text(json.dumps([{'id':d['id'],'name':d['display'],'view':v['id']} for d,v in records],ensure_ascii=False,indent=2),encoding='utf8')
    print('Rendered',len(records),'priority CAD views')

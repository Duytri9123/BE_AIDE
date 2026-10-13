"""Render existing SVG evidence and group unresolved projections for visual review."""
import json,io,re,xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter
import pymupdf
from PIL import Image,ImageDraw,ImageFont
BASE=Path(__file__).resolve().parents[1]
ROOT=BASE/'data/CatalogTB'
OUT=BASE.parent/'outputs/catalogtb-projection-review'
OUT.mkdir(exist_ok=True)
audit=json.loads((BASE.parent/'outputs/catalogtb-agent-audit/deep-recognition-audit.json').read_text(encoding='utf8'))
dimensions=json.loads((BASE.parent/'outputs/catalogtb-dimension-audit/audit.json').read_text(encoding='utf8'))
envelopes={(r['profile'],r['view']):r.get('cad_envelope') for r in dimensions['views']}
rows=[]
for asset in audit['views']:
    if asset['face']!='unknown' and asset['units_code']==4:continue
    path=Path(asset['path']);profile=ROOT/asset['profile']
    d=json.loads(profile.read_text(encoding='utf8'))
    view=next(v for v in d['cad_don'] if (profile.parent/v['duong_dan']).resolve()==path.resolve())
    svg=path.parent/'xem_truoc.svg'
    row={'number':len(rows)+1,'profile':asset['profile'],'view':view['id_hinh_goc'],'name':d['ten_san_pham'],'face':view.get('huong_nhin'),'units':asset['units_code'],'envelope':envelopes.get((asset['profile'],view['id_hinh_goc'])),'source':d.get('nguon_cad'),'image':f'{len(rows)+1:03d}.png'}
    try:
        # MuPDF does not apply these class styles; inline them in the review
        # copy only. Never change library SVG or DXF geometry.
        tree=ET.fromstring(svg.read_bytes());styles={}
        for node in tree.iter():
            if node.tag.endswith('style'):
                for name,body in re.findall(r'\.([\w-]+)\s*\{([^}]+)\}',node.text or ''):
                    styles[name]=dict(part.strip().split(':',1) for part in body.split(';') if ':' in part)
        for node in tree.iter():
            for cls in node.get('class','').split():
                for key,value in styles.get(cls,{}).items():
                    if value.strip()!='none' or key not in ('stroke-width',):node.set(key.strip(),value.strip())
        vector=pymupdf.open(stream=ET.tostring(tree),filetype='svg')
        pdf=pymupdf.open('pdf',vector.convert_to_pdf())
        page=pdf[0]; scale=min(380/page.rect.width,380/page.rect.height)
        pix=page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=True)
        im=Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGBA')
        bg=Image.new('RGBA',im.size,'#202830'); bg.alpha_composite(im);bg.convert('RGB').save(OUT/row['image'])
    except Exception as exc:row['render_error']=str(exc)
    rows.append(row)
(OUT/'evidence.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
for start in range(0,len(rows),16):
    sheet=Image.new('RGB',(1600,1800),'white');draw=ImageDraw.Draw(sheet)
    for j,row in enumerate(rows[start:start+16]):
        x=j%4*400;y=j//4*450
        if (OUT/row['image']).is_file():
            im=Image.open(OUT/row['image']);im.thumbnail((390,365));sheet.paste(im,(x+(400-im.width)//2,y))
        label=f"{row['number']} {row['name']}"
        draw.text((x+4,y+368),label[:49],fill='black',font=font)
        draw.text((x+4,y+388),label[49:98],fill='black',font=font)
        draw.text((x+4,y+409),str(row['envelope']),fill='black',font=font)
    sheet.save(OUT/f'sheet-{start//16+1:02d}.png')
print(json.dumps({'views':len(rows),'sheets':(len(rows)+15)//16,'render_errors':sum('render_error' in r for r in rows)}))

"""Read every uncatalogued source item and render category contact sheets."""
import hashlib,json,re
from collections import Counter,defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET
import ezdxf
import pymupdf
from PIL import Image,ImageDraw,ImageFont
from scripts.read_cad_evidence import extract

ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'data/CatalogTB'
OUT=ROOT/'outputs/source-630-review'


def main():
    OUT.mkdir(exist_ok=True,parents=True)
    sources=json.loads((CAT/'ai_library_manifest.json').read_text(encoding='utf8'))['source_cad_documents']
    rows=[]
    for index,source in enumerate(sources,1):
        p=CAT/source['path'];row=dict(source,index=index,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        meta=p.parent/'thong_tin.json'
        row['metadata']=json.loads(meta.read_text(encoding='utf-8-sig')) if meta.is_file() else {}
        if p.suffix.lower()=='.dxf':
            try:
                doc=ezdxf.readfile(p)
                row.update(texts=extract(doc),units=doc.units,entity_counts=dict(Counter(e.dxftype() for e in doc.modelspace())),
                           block_names=[b.name for b in doc.blocks if not b.name.startswith('*')][:100])
            except Exception as exc:row['error']=str(exc)
        else:row.update(texts=[],archive_only=True)
        rows.append(row)
        if index%100==0:print('Read',index,flush=True)
    (OUT/'inventory.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
    groups=defaultdict(list)
    for row in rows:groups[Path(row['path']).parts[0]].append(row)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13)
    for group,items in groups.items():
        for start in range(0,len(items),60):
            sheet=Image.new('RGB',(1600,1800),'white');draw=ImageDraw.Draw(sheet)
            for i,row in enumerate(items[start:start+60]):
                x=(i%5)*320;y=(i//5)*150
                draw.text((x+5,y+3),f"#{row['index']} {row['name'][:35]}",font=font,fill='black')
                preview=CAT/row['preview_path'] if row.get('preview_path') else None
                if not preview or not preview.is_file():continue
                try:
                    svg=ET.fromstring(preview.read_bytes())
                    rules={name:dict(part.strip().split(':',1) for part in body.split(';') if ':' in part)
                           for style in svg.iter('{http://www.w3.org/2000/svg}style')
                           for name,body in re.findall(r'\.([\w-]+)\s*\{([^}]+)\}',style.text or '')}
                    for node in svg.iter():
                        for name in node.attrib.get('class','').split():
                            for k,v in rules.get(name,{}).items():node.set(k.strip(),v.strip())
                    bounds=svg.attrib.get('viewBox','0 0 1000 1000').replace(',',' ').split()
                    svg.insert(0,ET.Element('{http://www.w3.org/2000/svg}rect',dict(x=bounds[0],y=bounds[1],width=bounds[2],height=bounds[3],fill='#212930')))
                    doc=pymupdf.open(stream=ET.tostring(svg),filetype='svg')
                    pdf=pymupdf.open(stream=doc.convert_to_pdf(),filetype='pdf');page=pdf[0]
                    scale=min(310/page.rect.width,116/page.rect.height)
                    pix=page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False)
                    photo=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
                    sheet.paste(photo,(x+(320-photo.width)//2,y+25))
                except Exception as exc:draw.text((x+5,y+50),str(exc)[:35],font=font,fill='red')
            slug=re.sub(r'[^\w-]','_',group)
            sheet.save(OUT/f'{slug}-{start//60+1}.png')
    print(json.dumps({'items':len(rows),'with_text':sum(bool(r.get('texts')) for r in rows),'errors':sum('error'in r for r in rows),'groups':{k:len(v) for k,v in groups.items()}},ensure_ascii=False))


if __name__=='__main__':main()

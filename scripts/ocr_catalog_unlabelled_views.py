"""OCR rendered source views whose DXF contains no readable model text.

OCR output is a search lead only; it never promotes a manufacturer or model.
"""
import hashlib
import json
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'data/CatalogTB'
sys.path.insert(0,str(ROOT.parent/'tmp/tudien_ocr'))
sys.path.insert(0,str(ROOT.parent/'tmp/catalog_identity_ocr_runtime'))
import pymupdf
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

OUT=ROOT/'outputs/catalog-identity-ocr'
LOCAL=threading.local()


def read_view(job):
    profile,view=job
    preview=(CAT/view['path']).with_name('xem_truoc.svg')
    if not preview.is_file():return {'profile':profile,'view':view['id'],'status':'no_preview'}
    digest=hashlib.sha256(preview.read_bytes()).hexdigest()
    cache=OUT/(hashlib.sha256((digest+':white-background-v2').encode()).hexdigest()[:24]+'.json')
    if cache.is_file():return {**json.loads(cache.read_text(encoding='utf8')),'profile':profile,'view':view['id']}
    result={'profile':profile,'view':view['id'],'preview_sha256':digest,'status':'machine_read_requires_review'}
    try:
        svg=ET.fromstring(preview.read_bytes())
        rules={name:dict(part.strip().split(':',1) for part in body.split(';') if ':' in part)
               for style in svg.iter('{http://www.w3.org/2000/svg}style')
               for name,body in re.findall(r'\.([\w-]+)\s*\{([^}]+)\}',style.text or '')}
        for node in svg.iter():
            for name in node.attrib.get('class','').split():
                for key,value in rules.get(name,{}).items():node.set(key.strip(),value.strip())
            # Dark foreground on white improves character contrast; geometry stays unchanged.
            if node.tag.rsplit('}',1)[-1] not in {'svg','style','defs','clipPath'}:
                if node.get('stroke') not in (None,'none'):node.set('stroke','#000000')
                if node.get('fill') not in (None,'none'):node.set('fill','#000000')
        # The renderer's full-page background is a direct SVG child. It must
        # remain white after normalizing the foreground to black.
        for child in svg:
            if child.tag.rsplit('}',1)[-1]=='rect' and child.get('x')=='0' and child.get('y')=='0':
                child.set('fill','#ffffff')
        doc=pymupdf.open(stream=ET.tostring(svg),filetype='svg')
        pdf=pymupdf.open(stream=doc.convert_to_pdf(),filetype='pdf');page=pdf[0]
        scale=1400/max(page.rect.width,page.rect.height)
        pix=page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False)
        output=cache.with_suffix('.png');Image.frombytes('RGB',(pix.width,pix.height),pix.samples).save(output)
        if not hasattr(LOCAL,'engine'):LOCAL.engine=RapidOCR(intra_op_num_threads=1,inter_op_num_threads=1)
        rows,_=LOCAL.engine(str(output))
        result['lines']=[{'text':r[1],'confidence':float(r[2]),'polygon':r[0]} for r in rows or []]
        result['render']=output.relative_to(ROOT).as_posix()
    except Exception as error:result.update(status='ocr_failed',error=type(error).__name__+': '+str(error)[:160])
    cache.write_text(json.dumps(result,ensure_ascii=False),encoding='utf8')
    return result


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    records=json.loads((ROOT/'app/data/catalog_source_identification.json').read_text(encoding='utf8'))['profiles']
    jobs=[(profile,v) for profile,r in records.items() if r['status']=='source_geometry_without_model_label' for v in r['views']]
    results=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for future in as_completed([pool.submit(read_view,job) for job in jobs]):
            results.append(future.result())
            if len(results)%20==0:print(f'OCR checked {len(results)}/{len(jobs)} unlabelled source views',flush=True)
    summary={'profiles':len({p for p,v in jobs}),'views':len(jobs),
        'views_with_text':sum(bool(r.get('lines')) for r in results),'failures':sum(r['status']=='ocr_failed' for r in results),
        'items':results,'recognition_is_verified':False}
    (ROOT/'docs/catalog-unlabelled-ocr.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in summary.items() if k!='items'}),flush=True)


if __name__=='__main__':main()

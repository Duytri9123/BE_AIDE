"""Compare all source previews with documented CAD views, including unlabelled CAD.

Candidates are visual research leads, never manufacturer/SKU confirmations.
No dimensions, source drawings or electrical facts are modified.
"""
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'tmp/tudien_ocr'))
sys.path.insert(0,str(ROOT.parent/'tmp/catalog_identity_ocr_runtime'))
import numpy as np
import pymupdf
from PIL import Image,ImageOps

CAT=ROOT/'data/CatalogTB'
CACHE=ROOT/'outputs/catalog-outline-descriptors'


def descriptor(path):
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    cache=CACHE/(digest+'.json')
    if cache.is_file():return json.loads(cache.read_text(encoding='utf8'))
    svg=ET.fromstring(path.read_bytes())
    rules={name:dict(part.strip().split(':',1) for part in body.split(';') if ':' in part)
        for style in svg.iter('{http://www.w3.org/2000/svg}style')
        for name,body in re.findall(r'\.([\w-]+)\s*\{([^}]+)\}',style.text or '')}
    for node in svg.iter():
        for name in node.attrib.get('class','').split():
            for key,value in rules.get(name,{}).items():node.set(key.strip(),value.strip())
        if node.tag.rsplit('}',1)[-1] not in {'svg','style','defs','clipPath'}:
            if node.get('stroke') not in (None,'none'):node.set('stroke','#000000')
            if node.get('fill') not in (None,'none'):node.set('fill','#000000')
    for child in svg:
        if child.tag.rsplit('}',1)[-1]=='rect' and child.get('x')=='0' and child.get('y')=='0':child.set('fill','#ffffff')
    with pymupdf.open(stream=ET.tostring(svg),filetype='svg') as doc:
        with pymupdf.open(stream=doc.convert_to_pdf(),filetype='pdf') as pdf:
            page=pdf[0];scale=512/max(page.rect.width,page.rect.height)
            pix=page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False)
            img=Image.frombytes('RGB',(pix.width,pix.height),pix.samples).convert('L')
    foreground=ImageOps.invert(img).point(lambda p:255 if p>80 else 0)
    bbox=foreground.getbbox()
    if not bbox:
        # Extremely thin source strokes can be below 80/255 after rasterization.
        foreground=ImageOps.invert(img).point(lambda p:255 if p>0 else 0)
        bbox=foreground.getbbox()
    if not bbox:raise ValueError('Empty foreground')
    crop=foreground.crop(bbox)
    array=np.asarray(crop.resize((32,32),Image.Resampling.BOX),dtype=np.float32)/255
    vector=array.flatten();norm=float(np.linalg.norm(vector))
    if norm==0:raise ValueError('Empty descriptor')
    value={'preview_sha256':digest,'aspect':crop.width/crop.height,'vector':(vector/norm).tolist()}
    cache.write_text(json.dumps(value),encoding='utf8')
    return value


def main():
    CACHE.mkdir(parents=True,exist_ok=True)
    evidence=json.loads((ROOT/'app/data/catalog_source_identification.json').read_text(encoding='utf8'))['profiles']
    entries=[];errors=[]
    for i,(profile,record) in enumerate(evidence.items(),1):
        raw=json.loads((CAT/profile).read_text(encoding='utf8'))
        kind=str((raw.get('catalog_tham_khao') or {}).get('category') or (raw.get('nhan_dien_ai') or {}).get('loai_thiet_bi_code') or profile.split('/')[0]).upper()
        for view in record['views']:
            path=(CAT/view['path']).with_name('xem_truoc.svg')
            try:desc=descriptor(path)
            except Exception as error:
                errors.append({'profile':profile,'view':view['id'],'error':str(error)[:150]});continue
            entries.append({'profile':profile,'view':view['id'],'path':view['path'],'category':kind,**desc})
        if i%150==0:print(f'Rendered image descriptors {i}/{len(evidence)}',flush=True)
    donors=[e for e in entries if evidence[e['profile']]['status']=='documented_source_label'
            and not evidence[e['profile']]['contains_multiple_components']]
    pools={}
    for e in donors:pools.setdefault(e['category'],[]).append(e)
    results={}
    for entry in entries:
        current=evidence[entry['profile']]
        if current['status'] in {'documented_source_label','generic_mechanical','drawing_or_assembly'}:continue
        pool=[e for e in pools.get(entry['category'],[]) if e['profile']!=entry['profile']
              and abs(math.log(e['aspect']/entry['aspect']))<0.25]
        if not pool:continue
        matrix=np.asarray([e['vector'] for e in pool],dtype=np.float32)
        scores=matrix@np.asarray(entry['vector'],dtype=np.float32)
        scored=sorted(((float(score)-0.25*abs(math.log(e['aspect']/entry['aspect'])),e) for score,e in zip(scores,pool)),key=lambda v:v[0],reverse=True)
        seen=set()
        for score,donor in scored:
            if score<0.75:break
            if donor['profile'] in seen:continue
            seen.add(donor['profile']);documented=evidence[donor['profile']]['documented_models']
            result={'source_view':entry['view'],'source_preview_sha256':entry['preview_sha256'],
                'source_dxf_sha256':next(v['sha256'] for v in current['views'] if v['id']==entry['view']),
                'candidate_profile':donor['profile'],'candidate_view':donor['view'],
                'candidate_preview_sha256':donor['preview_sha256'],
                'candidate_dxf_sha256':next(v['sha256'] for v in evidence[donor['profile']]['views'] if v['id']==donor['view']),
                'outline_score':round(score,4),'score_is_probability':False,
                'models':[{'brand':m['brand'],'model':m['model'],'documents':m['documents']} for m in documented],
                'basis':'normalized_rendered_outline_and_aspect_ratio','identity_verified':False,'manual_reviewed':False}
            results.setdefault(entry['profile'],[]).append(result)
            if len(seen)>=3:break
    for profile,values in results.items():
        unique={}
        for value in sorted(values,key=lambda v:v['outline_score'],reverse=True):unique.setdefault(value['candidate_profile'],value)
        results[profile]=list(unique.values())[:3]
    output={'checked_at':'2026-10-17','source_views':len(entries),'donor_views':len(donors),'profiles_with_candidates':len(results),
        'method':'Local rendered CAD image comparison; text is not required. Similarity is not proof of a model.',
        'errors':errors,'profiles':results}
    (ROOT/'app/data/catalog_visual_candidates.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in output.items() if k!='profiles'}),flush=True)


if __name__=='__main__':main()

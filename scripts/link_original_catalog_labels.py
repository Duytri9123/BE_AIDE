"""Recover labels from the original DWG only through recorded source anchors/blocks."""
import hashlib
import json
import math
from pathlib import Path
from ezdxf.tools.text import plain_mtext

ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'data/CatalogTB'


def text_value(value):
    if isinstance(value,dict):return str(value.get('text') or '')
    return str(value or '')


def main():
    original=json.loads((ROOT/'outputs/original-catalog-labels.json').read_text(encoding='utf8'))
    source=Path(original['source'])
    if hashlib.sha256(source.read_bytes()).hexdigest()!=original['sha256']:raise ValueError('Original DWG changed')
    blocks={b['name']:b for b in original['blocks']}
    inserts=[e for e in original['modelspace'] if e['type']=='INSERT' and e.get('insertionPoint')]
    scans=json.loads((ROOT/'docs/catalog-source-text-evidence.json').read_text(encoding='utf8'))
    for scan in scans['items']:
        context=[]
        for view in scan['views']:
            metadata=(CAT/view['path']).with_name('thong_tin_cad_chen.json')
            if not metadata.is_file():continue
            raw=json.loads(metadata.read_text(encoding='utf8'))
            shift=(raw.get('hinh_hoc_lap_dat') or {}).get('dich_chuyen_tu_hinh_goc_mm')
            if shift:
                point=(-shift['x'],-shift['y'])
                matched=[e for e in inserts if math.hypot(e['insertionPoint']['x']-point[0],e['insertionPoint']['y']-point[1])<=0.002]
                # Rounded source anchors must identify a unique insertion.
                if len(matched)==1:
                    entry=matched[0];observed=[]
                    for attribute in entry.get('attributes') or []:
                        value=text_value(attribute.get('text'))
                        if value:observed.append({'tag':attribute.get('tag'),'text':plain_mtext(value),'handle':attribute['handle']})
                    context.append({'view':view['id'],'basis':'unique_original_insertion_at_recorded_source_anchor',
                        'handle':entry['handle'],'block':entry['name'],'attributes':observed,
                        'dynamic_state_verified':False,'source_sha256':original['sha256']})
            # Follow only block definitions referenced in the exported source view.
            for name in view.get('referenced_blocks') or []:
                if name.startswith('*') or name not in blocks:continue
                block=blocks[name];values=[]
                for entity in block['labels']:
                    value=text_value(entity.get('text'))
                    if value:values.append({'tag':entity.get('tag'),'text':plain_mtext(value),'handle':entity['handle']})
                if values:context.append({'view':view['id'],'basis':'named_block_in_original_library',
                    'block':name,'attributes':values,'dynamic_state_verified':False,'source_sha256':original['sha256']})
        scan['original_dwg_context']=context
    scans['with_original_dwg_context']=sum(bool(r.get('original_dwg_context')) for r in scans['items'])
    (ROOT/'docs/catalog-source-text-evidence.json').write_text(json.dumps(scans,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'original_context_profiles':scans['with_original_dwg_context'],
        'original_attribute_values':sum(len(c['attributes']) for r in scans['items'] for c in r.get('original_dwg_context') or [])}))


if __name__=='__main__':main()

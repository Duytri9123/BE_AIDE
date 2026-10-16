"""Read every CatalogTB DXF/SVG, preserving every source byte."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET
import ezdxf


def main():
    root = Path(__file__).resolve().parents[1]/'data/CatalogTB'
    findings, hashes, counts = [], {}, Counter()
    paths = sorted(p for p in root.rglob('*') if p.suffix.lower() in {'.dxf','.svg'} and p.is_file())
    for i,p in enumerate(paths, 1):
        counts[p.suffix] += 1
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        if digest not in hashes:
            finding = None
            try:
                if p.suffix.lower()=='.dxf':
                    doc = ezdxf.readfile(p)
                    if len(doc.modelspace())==0:
                        finding = 'empty_modelspace'
                else:
                    element = ET.parse(p).getroot()
                    if element.tag.rsplit('}',1)[-1]!='svg':
                        finding = 'not_svg'
            except Exception as exc:
                finding = type(exc).__name__+': '+str(exc)[:250]
            hashes[digest] = finding
        if hashes[digest]:
            findings.append(dict(path=p.relative_to(root).as_posix(), issue=hashes[digest]))
        if i%500==0:print(f'Checked {i}/{len(paths)}', flush=True)
    report = dict(file_counts=dict(counts), unique_contents=len(hashes), findings=findings,
                  note='Technical readability check; does not certify physical likeness or every manufacturing dimension.')
    from app.services.cad.cabinet_templates import inventory,source_path
    active_forms={source_path(i).relative_to(root.resolve()).as_posix() for i in inventory()}
    active_views={(f.parent/v['duong_dan']).resolve().relative_to(root.resolve()).as_posix()
                  for f in root.rglob('thong_tin_thiet_bi.json')
                  for v in json.loads(f.read_text(encoding='utf-8-sig'))['cad_don']}
    for finding in findings:
        finding['active_equipment_view']=finding['path'] in active_views
        finding['active_form_source']=finding['path'] in active_forms
    dest = root.parents[1]/'docs/catalog-file-integrity.json'
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report if len(findings)<10 else {**report,'findings':len(findings)},ensure_ascii=False))


if __name__=='__main__':main()

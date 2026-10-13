"""Inventory every CAD file, keeping source sheets separate from insertable devices."""
from pathlib import Path
from collections import Counter
import json, sys, hashlib
import ezdxf

BASE=Path(__file__).resolve().parents[1]
ROOT=(BASE/'data/CatalogTB').resolve()
OUT=BASE.parent/'outputs/catalogtb-agent-audit'
sys.stdout.reconfigure(encoding='utf-8')
report=json.loads((OUT/'deep-recognition-audit.json').read_text(encoding='utf-8'))
manifest=json.loads((ROOT/'ai_library_manifest.json').read_text(encoding='utf-8'))
owners={p.parent.resolve():p.relative_to(ROOT).as_posix() for p in ROOT.rglob('thong_tin_thiet_bi.json')}
forms=json.loads((ROOT/'Form tủ/catalog.json').read_text(encoding='utf-8'))['shells']
form_owners={(ROOT/'Form tủ'/s['source_dxf']).resolve().parent:s['id'] for s in forms}
primary={Path(v['path']).resolve() for v in report['views']}
primary.update((ROOT/'Form tủ'/s['source_dxf']).resolve() for s in forms)
existing={v['path']:v for v in report['views']}
rows=[]
sources=[]
files=sorted(p for p in ROOT.rglob('*') if p.is_file() and p.suffix.lower() in ('.dxf','.dwg'))
for index,path in enumerate(files,1):
    relative=path.relative_to(ROOT).as_posix()
    owner=next((owners[p] for p in path.parents if p in owners),None)
    form=next((form_owners[p] for p in path.parents if p in form_owners),None)
    role=('catalogued_device_view' if path in primary and owner else 'catalogued_form' if path in primary
        else 'supporting_device_source' if owner else 'supporting_form_source' if form else 'source_document_without_device_profile')
    row=dict(path=relative,role=role,owner_profile=owner,owner_form=form,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    metadata=path.parent/'thong_tin.json'
    if metadata.is_file():
        try:
            data=json.loads(metadata.read_text(encoding='utf-8'))
            row['source_name']=data.get('ten_hinh') or data.get('ten') or data.get('name') or path.parent.name
            row['source_kind']=data.get('loai_hinh')
        except (ValueError,OSError):row['metadata_needs_review']=True
    if path.suffix.lower()=='.dwg':
        row.update(readable_by_dxf_loader=False,status='native_dwg_reader_required')
    else:
        try:
            prev=existing.get(str(path))
            if prev and prev.get('readable'):
                row.update(readable_by_dxf_loader=True,units_code=prev['units_code'],audit_error_count=prev['audit_error_count'],in_memory_fix_count=prev['in_memory_fix_count'])
            else:
                doc=ezdxf.readfile(path);audit=doc.audit()
                row.update(readable_by_dxf_loader=True,units_code=doc.units,
                    audit_error_count=len(audit.errors),in_memory_fix_count=len(audit.fixes))
        except Exception as exc:row.update(readable_by_dxf_loader=False,error=str(exc)[:300])
    rows.append(row)
    if role=='source_document_without_device_profile':
        sources.append(dict(path=relative,name=row.get('source_name') or relative,category='UNCLASSIFIED_SOURCE',
            status='source_document_requires_component_review',auto_select=False,insertable=False,
            metadata_present=metadata.is_file(),file_exists=True,
            preview_path=(path.parent/'xem_truoc.svg').relative_to(ROOT).as_posix() if (path.parent/'xem_truoc.svg').is_file() else None))
    if index%250==0:print(f'Checked {index}/{len(files)} physical CAD files',flush=True)

summary=dict(total_cad_files=len(rows),dxf_files=sum(r['path'].lower().endswith('.dxf') for r in rows),
    readable_dxf_files=sum(r.get('readable_by_dxf_loader',False) for r in rows),
    native_dwg_files=sum(r['path'].lower().endswith('.dwg') for r in rows),
    roles=dict(Counter(r['role'] for r in rows)),
    files_with_audit_errors=sum(r.get('audit_error_count',0)>0 for r in rows),
    files_repaired_in_memory=sum(r.get('in_memory_fix_count',0)>0 for r in rows))
manifest['physical_cad_file_summary']=summary
manifest['physical_cad_file_inventory']=rows
manifest['source_cad_documents']=sources
manifest['policy']['source_sheets_are_not_missing_device_profiles']=True
manifest['policy']['raw_source_document_is_not_insertable_device']=True
temporary=ROOT/'ai_library_manifest.json.tmp'
temporary.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
temporary.replace(ROOT/'ai_library_manifest.json')
report['complete_physical_cad_audit']=dict(summary=summary,files=rows)
(OUT/'deep-recognition-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False),flush=True)

"""Hide identical translated source geometry without deleting original files."""
import json
from collections import Counter
from pathlib import Path
import ezdxf
from scripts.process_source_cad_catalog import fingerprint

ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB'

def main():
    path=ROOT/'docs/source-630-catalog-processing.json'
    report=json.loads(path.read_text(encoding='utf8'));seen={}
    for i,row in enumerate(report['items'],1):
        if row['status'] in {'processed_empty_legacy_reference','processed_native_library_archive'}:continue
        p=CAT/row['source'];digest=fingerprint(ezdxf.readfile(p))
        if digest in seen:
            original=seen[digest]
            old=row.get('profile')
            if old and old!=original:
                profile=CAT/old;data=json.loads(profile.read_text(encoding='utf8'))
                data['browser_hidden']=True;data['source_catalog_review']['duplicate_of']=original
                profile.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
            row.update(status='processed_duplicate_geometry',profile=original,geometry_sha256=digest)
        else:
            seen[digest]=row['profile'];row['geometry_sha256']=digest
        if i%100==0:print('Compared',i,flush=True)
    report['summary']['statuses']=dict(Counter(r['status'] for r in report['items']))
    report['summary']['visible_information_profiles']=len(seen)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    manifest_path=CAT/'ai_library_manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf8'))
    index={r['source']:r for r in report['items']}
    for r in manifest['source_cad_documents']:
        updated=index[r['path']];r['status']=updated['status'];r['information_profile']=updated.get('profile')
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(report['summary'],ensure_ascii=False))

if __name__=='__main__':main()

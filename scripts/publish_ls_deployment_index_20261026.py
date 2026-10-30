"""Register reviewed additions in the asset-serving index before worker rollout."""
import json
from pathlib import Path
from ls_native_writer import ROOT,CAT
from publish_abb_ct_index import main as publish

def main():
    out=ROOT/'docs/ls-all-cad-2026-10-24'
    paths=[CAT/r['profile'] for r in json.loads((out/'mt-america-additions-20261025.json').read_text(encoding='utf8'))]
    paths += [CAT/r['profile'] for r in json.loads((out/'gmp-price-links-20261025.json').read_text(encoding='utf8'))]
    paths += [CAT/r['profile'] for r in json.loads((out/'bk05s-additions-20261026.json').read_text(encoding='utf8'))]
    report=[]
    for path in paths:
        profile=json.loads(path.read_text(encoding='utf8'))
        for view in profile['cad_don']:
            folder=(path.parent/view['duong_dan']).parent
            report.append(dict(family=path.parent.name,view=view['huong_nhin'],path=folder.relative_to(CAT).as_posix()))
    name='ls-deployment-20261026'
    (ROOT/'docs'/f'{name}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    publish([p.parent.name for p in paths],report_name=name,brand='LS',category='MIXED',profile_root='LS/ThietBi',refresh=False)
    (out/'deployment-index-20261026.json').write_text(json.dumps(dict(profiles=len(paths),views=len(report),profile_paths=[p.relative_to(CAT).as_posix() for p in paths]),indent=2),encoding='utf8')

if __name__=='__main__':main()

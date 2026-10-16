"""Export LS contactor states with synchronized native model/rating lookups."""
import json, os, re, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'tmp/accessory_source_review'
CATALOG=ROOT/'data/CatalogTB'

def main():
    inventory=json.loads((WORK/'supplier-inventory.json').read_text(encoding='utf-8-sig'))
    jobs=[]
    for path in (CATALOG/'LS/ThietBi').glob('MC_*/thong_tin_thiet_bi.json'):
        profile=json.loads(path.read_text(encoding='utf8'))
        sources=[s for s in inventory if s['attributes'].get('TYPE')==path.parent.name.replace('_','-')]
        if len(sources)!=1:continue
        source=sources[0]
        types=source['properties'].get('Type',{}).get('allowed',[])
        rates=source['properties'].get('Rate',{}).get('allowed',[])
        for view in profile.get('cad_don',[]):
            metadata=json.loads((path.parent/'HinhChieu'/view['id_hinh_goc']/'thong_tin.json').read_text(encoding='utf8'))
            option=metadata.get('trang_thai_block','')
            match=re.fullmatch(r'(\d+)A: Front View',option)
            if match:
                number=str(int(match[1]))
                rate=next((r for r in rates if r.rstrip('A').isdigit() and int(r.rstrip('A'))==int(number)),number+'A')
                models=[t for t in types if t in ('MC-'+number,'MC-'+number+'a')]
            elif option in ('Back View','Side View'):
                models=[t for t in types if t.endswith('/b' if option=='Back View' else '/s')]
                rate='None'
            else:continue
            if len(models)!=1 or rate not in rates:raise ValueError((path,option,models,rate))
            jobs.append({'profile':path.relative_to(CATALOG).as_posix(),'view':view['id_hinh_goc'],
                         'handle':source['handle'],'option':option,'model':models[0],'rate':rate,
                         'selected_attributes':{'TYPE':models[0],'RATE':'' if rate=='None' else rate}})
    assert jobs,'No states found'
    manifest=WORK/'ls-rated-state-jobs.json'
    manifest.write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding='utf8')
    jobfile=WORK/'ls-rated-state-jobs.txt'
    jobfile.write_text('\n'.join('\t'.join([j['handle'],j['option'],str(WORK/(j['view']+'-native-state.dxf')),j['model'],j['rate']]) for j in jobs),encoding='utf8')
    env=os.environ.copy();env['AIDE_STATE_JOBS']=str(jobfile)
    for job in jobs:
        for suffix in ('.dxf.ok','.dxf.error'):
            (WORK/(job['view']+'-native-state'+suffix)).unlink(missing_ok=True)
    with (WORK/'ls-rated-state-export.log').open('wb') as log:
        subprocess.run(['C:/Program Files/Autodesk/AutoCAD 2022/accoreconsole.exe','/i',str(WORK/'input.dwg'),'/s',str(WORK/'states.scr'),'/l','en-US'],env=env,stdout=log,stderr=log,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
    for job in jobs:
        source=WORK/(job['view']+'-native-state.dxf')
        assert source.with_suffix('.dxf.ok').read_text()==job['option']
    env['AIDE_STATE_MANIFEST']=str(manifest);env['AIDE_FORCE_STATES']='1'
    subprocess.run([str(ROOT/'venv/Scripts/python.exe'),'-X','utf8',str(ROOT/'scripts/restore_native_supplier_states.py')],env=env,check=True)
    print('Repaired native states:',len(jobs))

if __name__=='__main__':main()

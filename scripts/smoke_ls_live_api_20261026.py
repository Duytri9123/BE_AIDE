"""Read-only authenticated smoke checks; credentials remain in process memory."""
import argparse,hashlib,io,json,sqlite3,urllib.request
from datetime import timedelta
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.core.config import settings
from app.core.security import create_access_token
from sqlalchemy.engine import make_url

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/ls-all-cad-2026-10-24'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base',default='http://127.0.0.1:8000');parser.add_argument('--stage',default='after')
    args=parser.parse_args()
    url=make_url(settings.DATABASE_URL)
    assert url.drivername.startswith('sqlite'),'Use an approved existing session for non-SQLite deployments'
    path=Path(url.database).resolve()
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
        user=db.execute("SELECT id FROM users WHERE status='active' AND role='admin' LIMIT 1").fetchone()
    assert user,'No active deployment reviewer account'
    token=create_access_token(user[0],expires_delta=timedelta(minutes=10))
    def get(path,authenticated=True):
        headers={'Connection':'close'}
        if authenticated:headers['Authorization']='Bearer '+token
        with urllib.request.urlopen(urllib.request.Request(args.base+path,headers=headers),timeout=90) as response:
            return response.status,response.read(),response.headers
    report=dict(base=args.base,stage=args.stage,health=[],rows=[],assets=[])
    for _ in range(4):
        status,body,_=get('/health',False);assert status==200 and json.loads(body)['status']=='ok';report['health'].append(status)
    cases=[('ls-pdf:46324bfb04bb21ee','LX',True),('ls-pdf:d8b8b1b0b925c8fa','LAM',True),('ls-pdf:fd287f918146bcce','LA',False)]
    additions=json.loads((OUT/'bk05s-additions-20261026.json').read_text(encoding='utf8'))
    for a in additions:cases.append((a['price_ids'][0],'BK05S-T3 '+a['poles'],True))
    if args.stage!='before':
        mt=json.loads((OUT/'mt-america-additions-20261025.json').read_text(encoding='utf8'))
        cases.extend((a['price_ids'][0],a['model'],True) for a in mt)
        targeted=ROOT/'docs/ls-targeted-review-2026-10-26'
        for name in ['dc-additions.json','mccb-additions.json']:
            if (targeted/name).is_file():
                for item in json.loads((targeted/name).read_text(encoding='utf8')):
                    cases.extend((ident,model,True) for ident,model in zip(item['price_ids'],item['models']))
        if args.stage=='targeted-final':
            prices=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items']
            cases.extend((r['id'],r['sku'],r['sku']!='ABS202c') for r in prices
                         if str(r.get('brand')).lower() in ['ls','ls electric']
                         and r['sku'] in ['MR-4 (2NO+2NC)','AN-06D3-06H AH6','ABS202c'])
        gimac=ROOT/'docs/ls-gimac-review-2026-10-26/additions.json'
        if gimac.is_file():
            for item in json.loads(gimac.read_text(encoding='utf8')):
                cases.extend((ident,model,True) for ident,model in zip(item['price_ids'],item['models']))
    for row_id,model,expected in cases:
        public=hashlib.sha256(row_id.encode()).hexdigest()[:24]
        status,body,_=get('/api/v1/device-catalog/rows/'+public+'/detail');d=json.loads(body)
        devices=d['cad_devices']
        if args.stage!='before':assert bool(devices)==expected,(model,expected,len(devices))
        report['rows'].append(dict(model=model,status=status,cad_families=len(devices),views=[len(x['views']) for x in devices]))
        if model.startswith('GIMAC-1000 EX,M485'):
            assert len(devices)==1 and len(devices[0]['views'])==6
            assert 'EX,M485' in devices[0]['selected_model']
        if model.startswith('BK05S') and devices:
            assert len(devices)==1 and len(devices[0]['views'])==2
            assert devices[0]['selected_model']==model
            v=devices[0]['views'][0];asset=f"/api/v1/equipment-library/{devices[0]['id']}/views/{v['id']}/preview"
            s,b,h=get(asset);assert s==200 and b
            report['assets'].append(dict(model=model,kind='preview',status=s,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
    if args.stage!='before':
        import ezdxf
        index=json.loads((OUT/'deployment-index-20261026.json').read_text(encoding='utf8'))
        for name in ['dc-additions.json','mccb-additions.json']:
            if (targeted/name).is_file():
                index['profile_paths'].extend(a['profile'] for a in json.loads((targeted/name).read_text(encoding='utf8')))
        if gimac.is_file():
            index['profile_paths'].extend(a['profile'] for a in json.loads(gimac.read_text(encoding='utf8')))
        report['source_downloads']=[];report['grouped_downloads']=[]
        for relative in index['profile_paths']:
            profile=ROOT/'data/CatalogTB'/relative
            p=json.loads(profile.read_text(encoding='utf8'))
            cid='TB-'+hashlib.sha1(relative.encode()).hexdigest()[:16]
            for view in p['cad_don']:
                vid='v-'+hashlib.sha256(view['id_hinh_goc'].encode()).hexdigest()[:20]
                path=f'/api/v1/equipment-library/{cid}/views/{vid}/dxf'
                status,data,_=get(path+'?grouped=false&colored=false')
                expected=(profile.parent/view['duong_dan']).read_bytes()
                assert hashlib.sha256(data).digest()==hashlib.sha256(expected).digest()
                report['source_downloads'].append(dict(catalog_id=cid,view_id=vid,status=status,bytes=len(data),source_hash_matches=True))
            if 'BK05S' in relative or 'MT-150' in relative:
                status,data,_=get(path)
                doc=ezdxf.read(io.StringIO(data.decode('utf8')));audit=doc.audit()
                assert doc.units==4 and not audit.errors and b'BLOCKVISIBILITYPARAMETER' in data
                report['grouped_downloads'].append(dict(catalog_id=cid,status=status,bytes=len(data),units_mm=True,visibility_parameter=True,audit_errors=0))
    (OUT/('live-api-'+args.stage+'-20261026.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(base=args.base,stage=args.stage,health=report['health'],
                          row_checks=len(report['rows']),previews=len(report['assets']),
                          source_downloads=len(report.get('source_downloads',[])),
                          grouped_downloads=len(report.get('grouped_downloads',[]))),ensure_ascii=True),flush=True)

if __name__=='__main__':main()

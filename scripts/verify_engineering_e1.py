"""Read-only verification/export of the design created through the real UI."""
import collections
import csv
import json
from pathlib import Path
import sys
import urllib.request
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.core.security import create_access_token

out=Path(__file__).resolve().parents[2]/'outputs/cabinet-engineering-v2-20261124'
headers={'Authorization':'Bearer '+create_access_token('23')}
base='http://127.0.0.1:8000/api/v1/projects/51/'
def get(path):
    with urllib.request.urlopen(urllib.request.Request(base+path,headers=headers),timeout=30) as response:return json.load(response)
payload=get('cabinet-designs')
design=next(d for d in payload['designs'] if d['id']=='1c949059-c7d5-42b3-aa3d-ae3b14526395')
s=design['state'];devices={d['id']:d for d in s['customDevices']};ps=s['placements'];r=s['engineeringReport']
assert r['sourceCount']==11 and len(ps)==39 and r['addedCount']==28
assert len(s['supports'])==3 and not s['diagnostics']['collisions']
assert not s['annotations']
source=[p for p in ps if not devices[p['sourceId']].get('product',{}).get('auto_engineering')]
assert len(source)==11
mcbs=sorted([p for p in ps if devices[p['sourceId']]['product'].get('category')=='MCB'],key=lambda p:p['x'])
assert [devices[p['sourceId']]['product']['tag'] for p in mcbs]==[f'MCB-{i:02d}' for i in range(1,7)]
assert [devices[p['sourceId']]['product']['in_a'] for p in mcbs]==[20,30,20,30,20,20]
assert len({devices[p['sourceId']]['product']['source_references'][0]['occurrence_id'] for p in mcbs})==6
assert all(abs(b['x']-a['x']-devices[a['sourceId']]['width'])<.01 for a,b in zip(mcbs,mcbs[1:]))
counts=collections.Counter(devices[p['sourceId']]['product'].get('category') for p in ps)
assert counts['FUSE']==3 and counts['DUCT']==5 and counts['TERMINAL']==12 and counts['DIN_STOP']==6
assert counts['N_BAR']==counts['PE_BAR']==counts['DISTRIBUTION_BLOCK']==1
assert len(r['wireRoutes'])==36 and len(r['doorHarness'])==7
assert r['busbars']['neutral']['copperSectionMm2'] is None and r['busbars']['pe']['copperSectionMm2'] is None
assert r['busbars']['neutral']['length']!=r['busbars']['pe']['length']
assert r['loadReview']['overloadedAtFullSimultaneity']==['A','B']
plate=[p for p in ps if p.get('owner')=='mounting_plate']
bounds=r['bounds']
for p in plate:
    d=devices[p['sourceId']]
    assert p['x']>=bounds['x']-.01 and p['y']>=bounds['y']-.01
    assert p['x']+d['width']<=bounds['x']+bounds['width']+.01 and p['y']+d['height']<=bounds['y']+bounds['height']+.01
for i,a in enumerate(plate):
    da=devices[a['sourceId']]
    for b in plate[i+1:]:
        db=devices[b['sourceId']]
        assert min(a['x']+da['width'],b['x']+db['width'])-max(a['x'],b['x'])<=.01 or min(a['y']+da['height'],b['y']+db['height'])-max(a['y'],b['y'])<=.01,(a['id'],b['id'])
memory=get('design-learning')
assert memory['active_cases']==0,'Never create a production approval while verifying.'
(out/'final-saved-design.json').write_text(json.dumps(design,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'engineering-report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
rows=[]
for p in ps:
    d=devices[p['sourceId']];pr=d['product']
    rows.append({'id':p['id'],'name':d['name'],'category':pr.get('category'),'origin':'bổ sung thiết kế' if pr.get('auto_engineering') else 'nguồn bóc tách',
                 'tag':pr.get('tag',''),'current_a':pr.get('in_a',pr.get('requiredCurrentA','')),'x_mm':p['x'],'y_mm':p['y'],'z_mm':p['standoff'],
                 'width_mm':d['width'],'height_mm':d['height'],'depth_mm':d['depth'],'owner':p['owner'],'support':p.get('mountedSupportId',''),
                 'included_components':json.dumps(pr.get('assembly_components',[]),ensure_ascii=False)})
with (out/'all-devices-and-accessories.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
result={'project':51,'design_id':design['id'],'revision':payload['revision'],'dimensions':r['dimensions'],'source_devices':11,'design_additions':28,
        'categories':dict(counts),'din_rails':3,'illustrative_wire_routes':len(r['wireRoutes']),'door_harness_links_pending':len(r['doorHarness']),
        'no_panel_overlaps':True,'source_occurrence_order_verified':True,'no_automatic_device_labels':True,'approved_learning_cases':memory['active_cases'],
        'electrical_release':False,'tests':{'backend':24,'frontend':11},'form_study':{'modern_layout_records':110,'legacy_inventory':297,'legacy_dxf_inspected':28}}
(out/'verification-final.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))

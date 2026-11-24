"""Revise project 51 through the normal version-checked API; never approve learning."""
import copy
import json
from pathlib import Path
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.security import create_access_token

OUT = Path(__file__).resolve().parents[2] / 'outputs/e1-design-review-20261124'
OUT.mkdir(parents=True, exist_ok=True)
URL = 'http://127.0.0.1:8000/api/v1/projects/51/cabinet-designs'
HEADERS = {'Authorization': 'Bearer ' + create_access_token('23'), 'Content-Type': 'application/json'}

def request(data=None):
    req = urllib.request.Request(URL, data=json.dumps(data).encode() if data else None, headers=HEADERS, method='PUT' if data else 'GET')
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)

def rect(w, h):
    return [[0, 0], [w, 0], [w, h], [0, h], [0, 0]]

payload = request()
if any(p['id'] == 'E1-DUCT-L' for p in payload['designs'][0]['state']['placements']):
    raise SystemExit('This revision is already applied. Inspect current design before making another revision.')
(OUT / 'before-api.json').write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
s = payload['designs'][0]['state']
by_id = {p['id']: p for p in s['placements']}
devices = {d['id']: d for d in s['customDevices']}

def add(name, w, h, depth, category, x, y, ident, front=None, **extra):
    d = dict(id=ident + '-MODEL', name=name, width=w, height=h, depth=depth,
             profile='Phụ kiện phương án; chưa chọn mã', design_source='Bổ sung thiết kế, không phải thiết bị bóc tách E1',
             geometry_status='parametric_unverified', projectionOnly=False,
             product=dict(category=category, name=name, origin='design_added', approval_status='pending'),
             warnings=['Chưa xác nhận mã, định mức, lỗ gá và kích thước nhà sản xuất.'],
             front=dict(width=w, height=h, paths=front or [rect(w, h)]),
             side=dict(width=depth, height=h, paths=[rect(depth, h)]),
             top=dict(width=w, height=depth, paths=[rect(w, depth)]), **extra)
    s['customDevices'].append(d)
    p = dict(id=ident, sourceId=d['id'], x=x, y=y, standoff=0, owner='mounting_plate', rotation=0,
             autoMount=False, locked=False, cutout=dict(enabled=False, shape='circle', diameter=0, width=0, height=0))
    s['placements'].append(p)
    return p

def rail(ident, x, y, w):
    s['supports'].append(dict(id=ident, name='DIN35 phương án · kiểm tra ngàm theo mã', kind='din', x=x, y=y,
        width=w, height=35, thickness=1, standoff=7.5, railHeight=7.5, autoFit=False, parentSupportIds=[],
        paths=[rect(w, 35), [[0, 5], [w, 5]], [[0, 30], [w, 30]]]))

def label(ident, text, x, y, owner='mounting_plate'):
    s['annotations'].append(dict(id=ident, text=text, x=x, y=y, owner=owner))

# Preserve source circuit identities when material quantities had been grouped.
circuits = [
    ('TB-6', 'MCB-01', 'ĐÈN', 'A', 3300, 20, 3),
    ('TB-8', 'MCB-02', 'MÁY LẠNH 1', 'B', 5000, 30, 4),
    ('TB-7', 'MCB-03', 'Ổ CẮM', 'C', 3300, 20, 5),
    ('TB-9', 'MCB-04', 'MÁY LẠNH 2', 'A', 5000, 30, 6),
    ('TB-10', 'MCB-05', 'CỬA', 'B', 3300, 20, 7),
    ('TB-11', 'MCB-06', 'PCCC', 'C', 3300, 20, 8),
]
s['annotations'] = []
for i, (ident, tag, load, phase, power, current, occurrence) in enumerate(circuits):
    p = by_id[ident]
    original = devices[p['sourceId']]
    d = copy.deepcopy(original)
    d['id'] = 'E1-' + tag + '-MODEL'
    d['name'] = f'{tag} · {load} · 2P {current}A'
    refs = [r for r in original.get('source_references', []) if r.get('tag') == tag]
    assert len(refs) == 1
    d['source_references'] = refs
    d['product'].update(name=d['name'], tag=tag, source_references=refs,
                        connected_load=f'{load} · Pha {phase} · {power} W', in_a=current)
    s['customDevices'].append(d)
    p.update(sourceId=d['id'], x=142 + i * 36, y=235)
    label(tag, f'{i+1:02d}/{phase}', p['x'] + 2, 325)
    label(tag+'-I', f'{current}A', p['x'] + 2, 219)

by_id['TB-1'].update(x=197.5, y=435)
by_id['TB-2'].update(x=100, y=460, standoff=7.5, mountedSupportId='E1-DIN-FUSE', baseStandoff=0)
r = s['supports'][0]
r.update(x=130, y=258, width=240, autoFit=False, paths=[rect(240,35), [[0,5],[240,5]], [[0,30],[240,30]]])
rail('E1-DIN-FUSE', 85, 482.5, 48)
rail('E1-DIN-X', 130, 72.5, 240)

# Five open slotted ducts. Dimensions/slots are provisional, not a certified SKU.
for ident, x, y, w, h in [('L',35,80,25,580), ('R',440,80,25,580), ('TOP',60,635,380,25), ('MID',60,355,380,25), ('LOW',60,155,380,25)]:
    vertical = h >= w
    length = max(w,h)
    across = min(w,h)
    paths = [rect(w,h)]
    for along in range(0, int(length), 10):
        for cross in [0, across-1.5]:
            paths.append([[a+cross,b+along] if vertical else [b+along,a+cross] for a,b in rect(1.5,min(4,length-along))])
    add(f'Máng dây 25×40 · L{length} · tham khảo', w,h,40,'DUCT',x,y,'E1-DUCT-'+ident,paths,
        wiringDuct=dict(wall=1.5,slotPitch=10,slotWidth=6,lid=False,
        source='https://www.hellermanntyton.com/products/wiring-ducts-and-accessories/htwd-pn-25x40/184-10068'))

# Twelve separate L/N outgoing terminals; six pairs follow source circuit order.
for i, (_,tag,load,phase,power,current,_) in enumerate(circuits):
    for j, pole in enumerate(['L','N']):
        x=152+i*36+j*8
        p=add(f'X{i+1}{pole} · {load} · cầu đấu dự kiến',8,50,45,'TERMINAL',x,65,f'E1-X{i+1}-{pole}',
              [rect(8,50), [[4,4],[4,46]], rect(4,6)])
        p.update(standoff=7.5, autoMount=True, mountedSupportId='E1-DIN-X', baseStandoff=0)
    label('X'+str(i+1),f'X{i+1}',154+i*36,125)

add('Thanh phân phối N có đế cách điện · dự kiến',90,20,25,'N_BAR',330,475,'E1-N-BAR',
    [rect(90,20), [[8,10],[82,10]]])
add('Thanh PE + điểm liên kết vỏ/cánh · dự kiến',90,20,25,'PE_BAR',330,550,'E1-PE-BAR',
    [rect(90,20), [[8,10],[82,10]]])
for ident,x,y,w,railid in [('MCB-L',134,258,8,r['id']),('MCB-R',358,258,8,r['id']),('X-L',140,72.5,8,'E1-DIN-X'),('X-R',348,72.5,8,'E1-DIN-X'),('FU-L',92,482.5,8,'E1-DIN-FUSE'),('FU-R',118,482.5,8,'E1-DIN-FUSE')]:
    p=add('Chặn DIN · phương án',w,35,38,'DIN_STOP',x,y,'E1-STOP-'+ident)
    p.update(standoff=7.5, mountedSupportId=railid, autoMount=True, baseStandoff=0)

label('IN-PENDING','NGUỒN VÀO / HƯỚNG CÁP: CHƯA XÁC NHẬN',60,688)
label('MAIN','Q0 · 3P 32A / CAD HỌ CVS100',155,612)
label('MAIN-CHECK','32A: KIỂM TRA TẢI ĐỒNG THỜI',145,408)
label('FUSE','FU1 · 2A',85,550)
label('N','N · THAM KHẢO',325,510)
label('PE','PE · CHƯA ĐẤU',325,580)
for i in range(3): label('HL'+str(i+1),['HL-A','HL-B','HL-C'][i],170+65*i,650,'inner_door')
used={p['sourceId'] for p in s['placements']}
s['customDevices']=[d for d in s['customDevices'] if d['id'] in used]
s['selectedId']='';s['selectedIds']=[];s['selectedSupportIds']=[];s['supportActive']=False
s.pop('placements_info',None)
s['diagnostics']={'collisions':[], 'status':'Phương án đang kiểm tra, chưa duyệt điện'}
result=request(dict(designs=payload['designs'],revision=payload['revision']))
saved=request()
(OUT/'after-api.json').write_text(json.dumps(saved,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'revision':saved['revision'],'placements':len(s['placements']),'ducts':5,'terminals':12,'supports':len(s['supports']),'approved':False}))

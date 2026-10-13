"""Use the visible geometry of saved native block states, never hidden alternatives."""
import copy
import json
import logging
import re
from pathlib import Path
import ezdxf
from ezdxf import bbox
from ezdxf.addons import Importer
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page
from ezdxf.addons.drawing.properties import LayoutProperties

logging.disable(logging.CRITICAL)
BASE=Path(__file__).resolve().parents[2]
NATIVE=BASE/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/LS_D02_DU_LIEU_MOI/native'
ROOT=BASE/'BE_AIDE/data/CatalogTB/LS/ThietBi'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
manifest=read(NATIVE/'manifest.json')
variants=read(NATIVE/'variants.json')+read(NATIVE/'views.json')
lookup={}
for s in manifest:
    m=re.search(r'C(\d+)-I(\d+)$',s['id'])
    lookup[f'D02_cluster{m[1]}-V{int(m[2]):03d}']=s

def visible(doc, entities):
    for e in entities:
        if e.dxf.get('invisible',0):continue
        layer=doc.layers.get(e.dxf.layer)
        if layer.is_off() or layer.is_frozen():continue
        if e.dxftype()=='INSERT':
            yield from visible(doc,e.virtual_entities())
        elif e.dxftype() not in ('TEXT','MTEXT','ATTDEF','ATTRIB','DIMENSION','LEADER','VIEWPORT'):
            yield e

def save_view(folder, state, ident=None):
    ident=ident or state['id']
    source=NATIVE/(state['id']+'.dxf')
    assert source.is_file(),source
    original=ezdxf.readfile(source)
    # Importer and virtual_entities cannot retain ACIS connection geometry.
    # Stop rather than publish a device with silently missing terminals.
    unsupported=[e.dxftype() for block in original.blocks for e in block
                 if e.dxftype() in ('REGION','3DSOLID','BODY','SURFACE') and not e.dxf.get('invisible',0)]
    if unsupported:
        raise RuntimeError(f'{state["id"]}: native CAD export required for {sorted(set(unsupported))}')
    entities=list(visible(original,original.modelspace()))
    assert entities
    doc=ezdxf.new('R2018');doc.units=4
    imp=Importer(original,doc);imp.import_entities(entities);imp.finalize()
    for e in doc.modelspace():e.dxf.invisible=0
    ext=bbox.extents(doc.modelspace(),fast=True);assert ext.has_data
    option=state['option'];lower=option.lower()
    face='Mặt trước'
    if 'side' in lower:face='Mặt bên'+(' · kèm đầu nối' if 'connecting' in lower else '')
    elif 'back' in lower:face='Mặt sau'
    elif 'cover' in lower:face='Nắp che mặt trước'
    elif re.match(r'\d+A:',option,re.I):face='Mặt trước · '+str(int(option.split('A')[0]))+' A'
    dest=folder/'HinhChieu'/ident;dest.mkdir(parents=True,exist_ok=True)
    doc.saveas(dest/'ban_ve.dxf')
    backend=SVGBackend();Frontend(RenderContext(doc),backend).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#ffffff','#243b53',units=4,dark_background=False))
    (dest/'xem_truoc.svg').write_text(backend.get_string(Page(max(35,ext.size.x+8),max(35,ext.size.y+8))),encoding='utf-8')
    write(dest/'thong_tin.json',{'id':ident,'loai_hinh':'view','ten_hinh':face,
       'tep':{'cad_dxf':'ban_ve.dxf','preview':'xem_truoc.svg'},
       'kich_thuoc_hinh_mm':{'ngang':round(ext.size.x,2),'cao':round(ext.size.y,2)},
       'trang_thai_block':option,'ma_trang_thai_goc':state['id']})
    return ident

base_profiles=list(ROOT.rglob('thong_tin_thiet_bi.json'))
for path in base_profiles:
    profile=read(path)
    if profile.get('trang_thai_ls_da_cap_nhat'):continue
    originals=[(ident,lookup[ident]) for ident in profile['cac_hinh_cad'] if ident in lookup]
    if not originals:continue
    groups={}
    for ident,source in originals:
        prop=next((x for x in source['dynamic_properties'] if x['name']=='Options'),None)
        if not prop:continue
        states=[{'id':source['id'],'option':prop['value'],'original_id':ident}]+[dict(v) for v in variants if v['source_id']==source['id']]
        fronts=[x for x in states if 'front' in x['option'].lower()]
        for front in fronts:
            m=re.match(r'([1-4]P(?:\+N)?):',front['option'],re.I)
            poles=m[1].upper() if m else str(profile['thong_so'].get('so_cuc',profile['thong_so'].get('so_cuc_chinh',''))) or 'standard'
            group=groups.setdefault(poles,[])
            selected=[front]
            for state in states:
                op=state['option'].lower()
                match=re.match(r'([1-4]p(?:\+n)?):',op)
                if 'space' in op:continue
                if 'side' in op or 'back' in op or ('cover' in op and (not match or match[1].upper()==poles)):
                    selected.append(state)
            for state in selected:
                if state['id'] not in {x['id'] for x in group}:group.append(state)
    if not groups:continue
    default=next((k for k,ss in groups.items() if any('original_id' in s for s in ss)),next(iter(groups)))
    for poles,states in groups.items():
        p=copy.deepcopy(profile)
        folder=path.parent if poles==default else path.parent.with_name(path.parent.name+'_'+poles.replace('+','_'))
        folder.mkdir(parents=True,exist_ok=True)
        if poles!=default:
            p['ten_kieu']=p['ten_san_pham']=re.sub(r' · \d cực','',p['ten_san_pham'])+' · '+poles
        if re.fullmatch(r'[1-4]P(?:\+N)?',poles):
            p['thong_so']['so_cuc']=poles
            p['thong_so'].pop('so_cuc_chinh',None)
        ids=[save_view(folder,s,s.get('original_id')) for s in states]
        # A default source ID appears only on the default front projection.
        p['cac_hinh_cad']=ids;p.pop('cad_don',None);p.pop('cad_chen_tu',None)
        p['trang_thai_ls_da_cap_nhat']=True
        p['dac_diem']=[*p.get('dac_diem',[]),'Mỗi mặt CAD chỉ chứa phần hiển thị của trạng thái đã chọn. Nắp che là phương án biểu diễn khi đóng nắp, không phải một góc nhìn khác.']
        if p['ban_chat']=='Khởi động từ':
            models=[]
            for state in states:
                if 'front' not in state['option'].lower():continue
                attrs=state.get('attributes',{})
                model=attrs.get('TYPE')
                if not model:
                    src=next((s for s in manifest if s['id']==state['id']),None)
                    if src:model=next((a['text'] for a in src['attributes'] if a['tag']=='TYPE'),None)
                if model and model not in models:models.append(model)
            if models:
                p['ma_dong_san_pham']=' / '.join(models)
                p['ten_kieu']=p['ten_san_pham']='Khởi động từ LS '+' / '.join(models)+' · 3 cực'
        write(folder/'thong_tin_thiet_bi.json',p)
print('Native visibility states imported into LS profiles.')


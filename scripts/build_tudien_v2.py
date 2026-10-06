"""Build a separate, source-traceable library of empty shells and CAD parts.

No existing library, source drawing, or application database is overwritten.
"""
import collections
import hashlib
import json
import logging
import re
import shutil
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'tmp/tudien_deps'))
import ezdxf
from ezdxf import bbox
from ezdxf.addons import Importer
from ezdxf.addons.drawing import RenderContext, Frontend, svg, layout, config
from ezdxf.math import Matrix44

DATA = ROOT / 'data'
OLD = DATA / 'tudien'
OUT = DATA / 'thu_vien_tu_dien_v2'
logging.getLogger('ezdxf').setLevel(logging.ERROR)

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def norm(value):
    return unicodedata.normalize('NFKD', str(value).replace('đ','d').replace('Đ','D')).encode('ascii','ignore').decode().upper()

def slug(value):
    return re.sub(r'[^A-Z0-9.-]+','_',norm(value)).strip('._')[:85] or 'CHUA_XAC_DINH'

def hid(value):
    return hashlib.sha256(value.encode()).hexdigest()[:16]

# These exact source profiles were rendered and visually checked, including nested blocks.
# They contain enclosure steelwork, doors, hinges and locks, without electrical equipment.
SHELL_IDS = {
    '9fd7e36dbbe1731a218b','bbe72afb54d8142e1ece','fe6f8fec4582f1040540',
    '9f5437cf3dd5156a3c7f','ef7f2c2600c1d9d16d23','a53a115a1edb833d3d5d',
    '6e858ec175983e88759b','178451e758bc7d203a7d','7f448864f7feb1cc6c4e',
    'ef57a40a8718e9e210d2','66c7d5214385dd9342e0','8ae5c62c14693729ed7d',
    '45b9c47d0a10a44f766f','d92d9155d4e140cf364f','a5d0ae2dc6e88623b8c4',
}

# Specific categories precede broad electrical/component words.
RULES = [
 ('phu_kien','ban_le',r'BANLE|BAN LE|HINGE|\b[HB]L0\d|^TV-.*BL'),
 ('phu_kien','khoa_tu',r'KHOA|\bMS(?:722|303|308|325|406)|\bAB301|\bME ?4[01]'),
 ('phu_kien','khung_ga_co_khi',r'^BASE |THANH [UDZ]|THANH DOC|THANH NGANG|THANH GIANG|THANH BIT|THANH GA|^XA |ACB BASE|^GA ACB|^CANH |^COVER|^NO[C]? TU|^PL004|^KTRONG'),
 ('phu_kien','bulong_tai_treo',r'BULONG|BULON|\bECU\b|\bNUT\b|\bBOLT\b|SCREW|LIFTING|TAI TREO|TAI CAU|MOCCAU|^M\d+(X\d+)?$|RONDELLE'),
 ('phu_kien','mang_day_ray_din',r'DUCT|MANG DAY|DIN35|RAY DIN|END BRA[K]?ET|CHAN TER'),
 ('phu_kien','su_cach_dien',r'\bSU |^SU\d|PHIP|INSULATOR|^SM\d'),
 ('phu_kien','thanh_dong_dau_cos',r'PNE.BAR|CAU TIEP DIA|THANH CAI|THANH DONG|BUS ?BAR|\bCOS |^CE-'),
 ('phu_kien','cau_dau',r'TERMINAL|TEMINAL|CAU DAU|DOMINO|^TB-|^CTS?\s?\d|^CAUDK|DAU-DOC'),
 ('phu_kien','quat_loc_gio',r'FAN|QUAT|FILTER|LOC GIO'),
 ('phu_kien','lo_khoet_nhan',r'^LO |^OVAL|^E VIS|^VIS MC'),
 ('thiet_bi','dong_ho',r'AMPERE|AMPER|VONMET|VOLTMET|^V EMIC|^A EMIC|DONG HO|METER|CONG ?TO|DH_VOLT|MFM|600PSR'),
 ('thiet_bi','bien_dong',r'BIEN DONG|^EMIC-|^MSQ-|^EM4H|^CT\d*$|^CTT$'),
 ('thiet_bi','bo_nguon',r'S8FS|BO NGUON|NGUON 24|POWER SUPPLY'),
 ('thiet_bi','PLC',r'S7-12|SM1223|\bPLC\b|CPU 12'),
 ('thiet_bi','contactor',r'CONTACTOR|^MC[ _-]?\d|^HWLS CONTACTOR|^LC1|^CC MC'),
 ('thiet_bi','ro_le_timer',r'RELAY|TRUNG GIAN|TIMER|\bOLR\b|\bMT[- ]?\d|^LRD\d|GRM8'),
 ('thiet_bi','den_bao',r'LIGHT|DEN BAO|^DEN (DO|XANH|VANG)|^DCHINT'),
 ('thiet_bi','nut_nhan_chuyen_mach',r'BUTTON|EMERGENCY|SELECTOR|CHUYEN MACH|SWITCH|DUNG KHAN|^NN |KBF-|KBD-'),
 ('thiet_bi','cau_chi',r'FUSE|CAU CHI|RT18|RT36|^C100'),
 ('thiet_bi','o_cam',r'O CAM|CAM 32|SOCKET'),
 ('thiet_bi','SPD',r'CHONG SET|\bSPD\b'),
 ('thiet_bi','dieu_khien_tu_bu',r'MIKRO|SMART ?GEN|APFC'),
 ('thiet_bi','tu_bu',r'KVAR|CAPACITOR|CUON KHANG'),
 ('thiet_bi','MCB',r'\bMCB|\bBKN|\bBKH|NXB|NB1-|IC60|LA63'),
 ('thiet_bi','MCCB',r'MCCB|ABN|ABS|ABH|EZC|CVS|NSX|NXM|GOPACT|METASOL|^BM |BM250|^TS\d|HGM|HGN|HG.SERI|HGC'),
 ('thiet_bi','ACB',r'\bACB|NXA|AN-AS-AH|HGN\(S\)'),
 ('thiet_bi','ELCB',r'ELCB'),
 ('thiet_bi','RCBO',r'RCBO'),
 ('thiet_bi','RCCB',r'RCCB'),
]

def classify(name):
    key=norm(name)
    if re.search(r'KHUNG BAN VE|KHUNG TEN|KHUNGTEN|BANG THONG SO|STANDARD ISO|LOGO|NAMELOAD|NAMELOAD|MARKING|^_OPEN|^_ARCH|^_DOT',key):
        return None
    if key.startswith(('A$','*')):
        return None
    for kind, category, pattern in RULES:
        if re.search(pattern,key):
            return kind, category
    return None

def maker(value):
    key=norm(value)
    if key.startswith('LS_') or key=='LS':return 'LS'
    for name in ['Schneider','Mitsubishi','ABB','CHINT','Siemens','LS','EMIC','Samwha','Omron','Idec','Selec','Shihlin','Hyundai','Himel','Mikro','Autonics','RISESUN','ROBOT','Hager','Panasonic','SmartGen','Fuji','Sino']:
        if re.search(r'(?<![A-Z])'+norm(name)+r'(?![A-Z])',key):return name
    return 'chua_xac_dinh'

def face(name):
    key=norm(name)
    for token,value in [('EQUIPMENT VIEW','mat_lap_thiet_bi_trong'),('E-SIDE','mat_hong_trong'),('REAR','mat_sau'),('2ND DOOR','canh_trong'),('1ST DOOR','canh_ngoai'),('FRONT','mat_truoc'),('SIDE','mat_hong'),('TOP','mat_tren'),('BOTTOM','mat_day')]:
        if token in key:return value
    return 'chua_xac_dinh'

def flatten(entities, stats, depth=0):
    if depth>24:raise ValueError('Nested block depth exceeds 24')
    for ent in entities:
        if ent.dxf.get('invisible',0):
            stats['hidden_removed']+=1;continue
        typ=ent.dxftype()
        if typ in ('TEXT','MTEXT','ATTRIB','ATTDEF','DIMENSION','LEADER','MLEADER','OLE2FRAME','IMAGE','VIEWPORT','ACAD_TABLE','WIPEOUT'):
            stats['annotations_removed']+=1;continue
        if typ=='INSERT':
            inserts=ent.multi_insert() if ent.mcount>1 else [ent]
            for ins in inserts:
                def skipped(entity, reason):
                    stats['unsupported'].append({'type':entity.dxftype(),'reason':reason})
                yield from flatten(ins.virtual_entities(skipped_entity_callback=skipped),stats,depth+1)
        else:
            yield ent.copy()

def export_geometry(source, folder):
    folder.mkdir(parents=True,exist_ok=True)
    signature=hashlib.sha256(source.read_bytes()).hexdigest()
    cached=folder/'geometry_report.json'
    if cached.exists() and (folder/'preview.svg').exists():
        report=load(cached)
        if report.get('source_sha256')==signature and report.get('export_version')==3 and (folder/report.get('cad_filename','cad.dxf')).exists():return report
    source_doc=ezdxf.readfile(source)
    doc=ezdxf.new('R2018');doc.units=source_doc.units
    importer=Importer(source_doc,doc)
    importer.import_tables(['linetypes','layers'])
    importer.finalize()
    stats={'hidden_removed':0,'annotations_removed':0,'unsupported':[]}
    for ent in flatten(source_doc.modelspace(),stats):
        doc.modelspace().add_entity(ent)
    bounds=bbox.extents(doc.modelspace(),fast=True)
    if not bounds.has_data or not len(doc.modelspace()):raise ValueError('No physical geometry after removing annotations')
    for ent in doc.modelspace():ent.transform(Matrix44.translate(-bounds.extmin.x,-bounds.extmin.y,0))
    cad_file=folder/'cad.dxf'
    try:doc.saveas(cad_file)
    except PermissionError:
        # A CAD viewer can hold the old file open on Windows; export to a new path.
        cad_file=folder/'cad_v3.dxf';doc.saveas(cad_file)
    cfg=config.Configuration(background_policy=config.BackgroundPolicy.WHITE,color_policy=config.ColorPolicy.BLACK)
    backend=svg.SVGBackend();Frontend(RenderContext(doc),backend,config=cfg).draw_layout(doc.modelspace(),finalize=True)
    (folder/'preview.svg').write_text(backend.get_string(layout.Page(240,180,layout.Units.mm,margins=layout.Margins.all(5))),encoding='utf8')
    report={'export_version':3,'cad_filename':cad_file.name,'source_sha256':signature,'entity_count':len(doc.modelspace()),'units_code':doc.units,
            'drawing_extent':{'width':bounds.size.x,'height':bounds.size.y,'depth':bounds.size.z},
            'normalization_offset':[bounds.extmin.x,bounds.extmin.y,0],
            'dimension_status':'drawing_extent_only_not_product_dimensions',**stats}
    save(cached,report)
    return report

GROUP_MAP={'Thiết bị đóng cắt':'dong_cat','Contactor':'contactor','Biến dòng':'bien_dong','Đồng hồ và công tơ':'dong_ho','Bản lề':'ban_le','Khóa tủ':'khoa_tu','Cơ khí tủ':'khung_ga_co_khi','Máng dây và ray DIN':'mang_day_ray_din','Nhãn và mặt che':'lo_khoet_nhan','Sứ và giá đỡ':'su_cach_dien','Thanh đồng và đầu nối':'thanh_dong_dau_cos','Cầu đấu':'cau_dau','Quạt và lọc gió':'quat_loc_gio','Nút nhấn và còi':'nut_nhan_chuyen_mach','Rơ le và timer':'ro_le_timer','Cầu chì':'cau_chi','Đèn báo':'den_bao','Ổ cắm':'o_cam','Bộ nguồn DC':'bo_nguon','Bộ điều khiển':'dieu_khien','Tụ bù và cuộn kháng':'tu_bu','Biến tần':'bien_tan','Biến áp và ổn áp':'bien_ap','Chống sét':'SPD'}

def location(category):
    if category in ('ban_le','khoa_tu','bulong_tai_treo','quat_loc_gio','lo_khoet_nhan'):return 'tren_vo_canh_tu'
    if category in ('mang_day_ray_din','su_cach_dien','thanh_dong_dau_cos','cau_dau'):return 'trong_tu'
    return 'chua_xac_dinh'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    legacy=load(DATA/'catalog_data.json')
    catalog_brand_tokens=collections.defaultdict(set)
    for row in legacy:
        for token in [row['series'],row['ma'].split()[0]]:
            token=re.sub(r'[^A-Z0-9]','',norm(token))
            if len(token)>=5:catalog_brand_tokens[token].add(maker(row['brand']))
    def resolve_brand(name, texts, existing=None):
        known=maker(existing or '')
        if known=='chua_xac_dinh':known=maker(name+' '+' '.join(texts))
        if known!='chua_xac_dinh':return known,'source_name_text_or_reviewed_library_evidence'
        tokens={re.sub(r'[^A-Z0-9]','',t) for t in re.findall(r'[A-Z0-9]+(?:[-.][A-Z0-9]+)*',norm(name))}
        candidates=set().union(*(catalog_brand_tokens.get(t,set()) for t in tokens))
        if len(candidates)==1:return next(iter(candidates)),'unique_model_token_in_supplied_catalog_not_manufacturer_certification'
        return known,'not_inferred_from_filename'
    profiles=load(OLD/'geometry_profiles.json')
    coverage=load(OLD/'coverage.json')
    source_names={x['id']:x['source_file'] for x in coverage}
    save(OUT/'nguon/catalog_data_goc.json',legacy)
    save(OUT/'nguon/coverage_tudien.json',coverage)
    save(OUT/'nguon/catalog_accessories_goc.json',load(DATA/'catalog_accessories.json'))
    assets=[];pending=[];failures=[];profile_assets={}
    def add_asset(key,name,kind,category,brand,source,evidence,view='chua_xac_dinh',pol=None):
        folder=OUT/kind
        if kind=='phu_kien':folder/=location(category)
        folder=folder/category/slug(brand)/(slug(name)+'__'+key)
        try:report=export_geometry(source,folder)
        except Exception as exc:
            failures.append({'id':key,'source':str(source),'error':str(exc)});return None
        item={'id':key,'name':name,'kind':kind,'category':category,'manufacturer':brand,'poles':pol,'view':view,
              'cad':(folder/report.get('cad_filename','cad.dxf')).relative_to(OUT).as_posix(),'preview':(folder/'preview.svg').relative_to(OUT).as_posix(),
              'metadata':(folder/'metadata.json').relative_to(OUT).as_posix(),'geometry':report,'evidence':evidence,
              'sku_ids':[],'technical_verification':'source_drawing_not_manufacturer_certified'}
        if kind=='form_tu':
            item.update(contains_electrical_equipment=False,visual_review='rendered_and_reviewed_empty_shell',
                        scope='multi_view_empty_enclosure' if 'Wall Mount' in name else 'empty_enclosure_view',
                        included_parts=['vo_khung','canh_tam','lo_khoet','phu_kien_co_khi_gan_vo'])
        if kind=='phu_kien':item['mounting_location']=location(category)
        assets.append(item)
        return item
    visible_names={n for g in profiles if 'hidden_entity_count_removed' in g for n in g['block_names']}
    for i,g in enumerate(profiles):
        names=' / '.join(g['block_names']);is_visible='hidden_entity_count_removed' in g
        if g['id'] in SHELL_IDS:
            kind,category='form_tu','vo_tu_treo' if 'Wall Mount' in names else 'vo_tu_ghep_khung'
        else:
            selection=classify(names)
            if not is_visible and any(n in visible_names for n in g['block_names']):selection=None
            if not selection:
                pending.append({'id':g['id'],'names':g['block_names'],'source_cad':'../tudien/'+g['cad_views']['source_view'],
                                'reason':'superseded_dynamic_parent_or_unclassified_or_annotation','sources':g['sources']});continue
            kind,category=selection
        texts=g.get('visible_labels',[])
        brand,brand_basis=resolve_brand(names,texts)
        evidence={'origin':'Tudien','source_profile_id':g['id'],'source_blocks':g['block_names'],'texts':texts,
                  'sources':[{**s,'source_filename':source_names.get(s['source_id'])} for s in g['sources']],
                  'brand_basis':brand_basis}
        a=add_asset('td_'+g['id'],names,kind,category,brand,OLD/g['cad_views']['source_view'],evidence,face(' '.join(texts)+' '+names),g.get('poles_from_visible_label'))
        if a:profile_assets[g['id']]=a['id']
        if i%100==0:print('Tudien',i,'assets',len(assets),flush=True)
    reviewed_forms=load(Path(__file__).with_name('tudien_v2_reviewed_forms.json'))
    form_manifest=load(DATA/'cabinet_templates/formtu/manifest.json')['items']
    form_by_id={f['id']:f for f in form_manifest}
    for review in reviewed_forms:
        f=form_by_id[review['id']]
        source=DATA/'cabinet_templates/formtu'/f['filename']
        doc=ezdxf.readfile(source)
        for ent in list(doc.modelspace().query('INSERT')):
            if ent.dxf.name==f['source_block']:doc.modelspace().delete_entity(ent)
        staging=OUT/'nguon/formtu_bo_khung_ten'/f['filename']
        staging.parent.mkdir(parents=True,exist_ok=True)
        if not staging.exists():doc.saveas(staging)
        dims=f['dimensions'];name='Vo tu '+str(dims['height'])+'x'+str(dims['width'])+'x'+str(dims['depth'])+' '+f['id']
        a=add_asset('shell_'+f['id'],name,'form_tu','vo_tu_'+f['kind'],'chua_xac_dinh',staging,
                    {'origin':'FOMTU','source_sheet':f['id'],'source_file':f['source_file'],'source_title':f['description'],
                     'title_attributes':f['attributes'],'review':review},'nhieu_mat_vo_tu')
        if a:
            a.update(scope='multi_view_empty_enclosure',dimensions_mm_from_source_title=dims,
                     dimensions_basis='title_attributes_not_independently_certified',visual_review=review['visual_review'])
    # Existing CAD libraries supply actual component drawings, not generated placeholders.
    manifests={}
    for file in (DATA/'device_layouts').glob('*/manifest.json'):
        for item in load(file)['items']:manifests[item['id']]=(item,file.parent)
    registry=load(DATA/'cad_device_registry.json')
    for index,group in enumerate(registry['devices']):
        for view in group['views']:
            aid=view['asset_id']
            if aid not in manifests:failures.append({'missing_old_asset':aid});continue
            original,base=manifests[aid]
            name=original.get('source_block') or original['name']
            kind='phu_kien' if group['kind']=='accessory' else 'thiet_bi'
            category=GROUP_MAP.get(group['group'],'chua_phan_loai')
            correction=classify(name)
            if correction:kind,category=correction
            evidence={'origin':'existing_cad_library','asset_id':aid,'source_file':original.get('source_file'),'source_block':name,
                      'texts':group.get('recognition',{}).get('texts',[]),'recognition':group.get('recognition',{}),
                      'original_group':group['group'],'original_filename':str(base/original['filename'])}
            brand,brand_basis=resolve_brand(name,evidence['texts'],group['brand'])
            evidence['brand_basis']=brand_basis
            add_asset('lib_'+aid,name,kind,category,brand,base/original['filename'],evidence,view['face'])
        if index%100==0:print('Existing catalog CAD',index,'assets',len(assets),flush=True)
    # Link ordering data to CAD with an explicit evidence level. No unverified geometry is approved for manufacture.
    sku_records=[]
    def tokens(value):return re.findall(r'[A-Z0-9]+(?:[-.][A-Z0-9]+)*',norm(value))
    def compact(value):return re.sub(r'[^A-Z0-9]','',norm(value))
    for index,row in enumerate(legacy):
        brand=maker(row['brand']);series=compact(row['series']);sku_id='sku_'+hid(row['brand']+'|'+row['ma'])
        links=[]
        for a in assets:
            if a['kind']!='thiet_bi' or a['manufacturer']!=brand:continue
            text=a['name']+' '+' '.join(a['evidence'].get('texts',[]))
            model_tokens={compact(t) for t in tokens(text)}
            # Full series token, not substring: MC-9 cannot match MC-95.
            exact_model=compact(row['ma']) in model_tokens
            if not exact_model and (len(series)<3 or series not in model_tokens):continue
            source_poles=a.get('poles') or next(iter(re.findall(r'\b([1-4])P\b',norm(text))),None)
            source_poles=int(str(source_poles).replace('P','')) if source_poles else None
            if source_poles and row.get('p') and source_poles!=row['p']:continue
            extent=a['geometry']['drawing_extent']
            dimensional_match=bool(row.get('w') and row.get('h') and abs(extent['width']-row['w'])<1 and abs(extent['height']-row['h'])<1)
            links.append({'asset_id':a['id'],'cad':a['cad'],'preview':a['preview'],'status':'series_reference_requires_model_check',
                          'evidence':{'series_token':row['series'],'exact_order_code_token':exact_model,'brand':brand,'source_poles':source_poles,'catalog_poles':row.get('p'),'front_extent_matches_catalog_within_1_drawing_unit':dimensional_match},
                          'approved_for_manufacture':False})
            a['sku_ids'].append(sku_id)
        sku_records.append({'id':sku_id,'sku':row['ma'],'name':row['n'],'manufacturer':brand,'category':row['t'],'series':row['series'],
                            'specifications':{k:v for k,v in row.items() if k not in ('ma','n','brand','brand_display','series','t')},
                            'source_catalog_record':index,'cad_links':links,'cad_status':'has_reference_drawing' if links else 'no_matching_source_drawing'})
    # Quotation records retain their source/row references; they do not become invented CAD models.
    quotation=load(OLD/'sku_registry.json')
    forms=[a for a in assets if a['kind']=='form_tu']
    arrangements=[]
    for frame in load(OLD/'form_tu/frames.json'):
        f=load(OLD/frame['path'])
        mapped=[]
        asset_index={a['id']:a for a in assets}
        for p in f['placements']:
            if p.get('geometry_profile_id') not in profile_assets:continue
            aid=profile_assets[p['geometry_profile_id']]
            transform=p.get('normalized_to_source_matrix')
            if transform:
                offset=asset_index[aid]['geometry']['normalization_offset']
                transform=list(Matrix44.translate(*offset)*Matrix44(transform))
            mapped.append({'source_handle':p['handle'],'asset_id':aid,
                           'source_transform':transform,'source_world_bounds':p.get('visible_world_bounds'),
                           'transform_basis':'new CAD normalization offset composed with original normalized-to-source transform'})
        arrangements.append({'id':frame['id'],'source_title':frame['name'],'source_id':frame['source_id'],
                             'kind':'assembled_layout_reference_not_empty_form','parts':mapped,'source_layout':'../tudien/'+frame['path']})
    for a in assets:save(OUT/a['metadata'],a)
    save(OUT/'catalog.json',{'schema_version':2,'name':'Thư viện vỏ tủ, thiết bị và phụ kiện','source_catalog':'nguon/catalog_data_goc.json',
                            'definitions':{'form_tu':'Vỏ/khung tủ trống, không có thiết bị điện; gồm cánh, tấm và chi tiết cơ khí gắn vỏ. Khung tên bản vẽ không phải form tủ.',
                                           'drawing_extent':'Bao hình CAD, không thay thế kích thước sản phẩm trong catalog.',
                                           'cad_links':'Liên kết có bằng chứng series/hãng; trạng thái xác minh được lưu riêng.'},
                            'forms':forms,'products':sku_records,'cad_assets':assets,'quotation_products':quotation})
    save(OUT/'form_tu/index.json',forms)
    save(OUT/'thiet_bi/index.json',[a for a in assets if a['kind']=='thiet_bi'])
    save(OUT/'phu_kien/index.json',[a for a in assets if a['kind']=='phu_kien'])
    save(OUT/'bo_tri_da_lap/index.json',arrangements)
    save(OUT/'cho_doi_chieu/geometry_chua_phan_loai.json',pending)
    save(OUT/'cho_doi_chieu/sku_chua_co_cad.json',[s for s in sku_records if not s['cad_links']])
    save(OUT/'cho_doi_chieu/loi_xuat.json',failures)
    reviewed_ids={f['id'] for f in reviewed_forms}
    save(OUT/'cho_doi_chieu/formtu_sheets_chua_xac_nhan_vo_trong.json',[f for f in form_manifest if f['id'] not in reviewed_ids])
    summary={'source_files_tudien':len(coverage),'catalog_products':len(sku_records),'quotation_products':len(quotation),
             'cad_assets':len(assets),'by_kind':dict(collections.Counter(a['kind'] for a in assets)),
             'empty_shell_multi_view_sets':sum(a.get('scope')=='multi_view_empty_enclosure' for a in forms),
             'empty_shell_other_view_assets':sum(a.get('scope')=='empty_enclosure_view' for a in forms),
             'products_with_reference_cad':sum(bool(s['cad_links']) for s in sku_records),'products_without_cad':sum(not s['cad_links'] for s in sku_records),
             'unclassified_or_superseded_profiles':len(pending),'export_errors':len(failures)}
    save(OUT/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()

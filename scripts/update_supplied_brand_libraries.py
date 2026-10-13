"""Import named source references conservatively, retaining provenance and review gates."""
import collections, hashlib, json, logging, re, shutil, sys
from pathlib import Path
import ezdxf
from ezdxf import bbox
from ezdxf.lldxf.tagwriter import TagCollector
from ezdxf.addons import Importer
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page
from ezdxf.addons.drawing.properties import LayoutProperties

BASE=Path(__file__).resolve().parents[1]; ROOT=BASE/'data/CatalogTB'
logging.disable(logging.CRITICAL)
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def save(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def file_units(path):
    with path.open('rb') as stream:header=stream.read(20000).decode('ascii','ignore')
    match=re.search(r'\$INSUNITS\s+70\s+(\d+)',header)
    return int(match[1]) if match else 0
def visible(doc,es,depth=0):
    if depth>30:return
    for e in es:
        if e.dxf.get('invisible',0):continue
        layer=doc.layers.get(e.dxf.layer)
        if layer.is_off() or layer.is_frozen():continue
        if e.dxftype()=='INSERT':yield from visible(doc,e.virtual_entities(),depth+1)
        elif e.dxftype() not in ('TEXT','MTEXT','ATTRIB','ATTDEF','DIMENSION','LEADER','VIEWPORT','HATCH','POINT'):
            yield e
def fingerprint(es):
    b=bbox.extents(es,fast=True)
    if not b.has_data:return None
    c=b.center;keys=[]
    for e in es:
        try:
            v=e.copy();v.translate(-c.x,-c.y,-c.z)
            tags=TagCollector.dxftags(v)
            key=[]
            for code,value in tags:
                if code in (5,102,330,360,8,6,62,420,370,48,67,410) or code>=1000:continue
                if isinstance(value,(float,int)):value=round(float(value),3) or 0.0
                elif hasattr(value,'x'):value=tuple(round(float(x),3) or 0.0 for x in value)
                key.append((code,value))
            keys.append(repr(key))
        except Exception:keys.append(e.dxftype()+repr(e.dxf.all_existing_dxf_attribs()))
    return hashlib.sha256('\n'.join(sorted(keys)).encode()).hexdigest()
def relevant(brand,name):
    n=name.upper()
    if brand=='LS':return bool(re.search(r'\bLS\b|\b(?:MC|MT|OLR|AUX|ABN|ABS|ABH|ABE|BKN|BKH|BKD|RKP|RKN|BS32|32KGR|TS1600|SUSOL|METASOL)',n)) and 'LOGO' not in n
    if brand=='Chint':return bool(re.search(r'\b(?:NXM|NXB|NM1|NZ7|CHINT|CJX|NXC|NXR|RT36|RT18|NP2|KG316|XJ3|RJ25)',n))
    return (n.startswith('06 - N - SC ') or bool(re.match(r'(?:SN_|LC1|LV429640|NSX|NS\d|CVS|EZC)',n)))
def purpose(name):
    n=name.upper()
    for pattern,kind,use in [
        (r'VSD|ATV','Biến tần','Điều khiển động cơ; cần xác nhận cấu hình và sơ đồ cọc.'),
        (r'ROLE NHIỆT|\bMT|OLR|LRD|NXR','Rơ le nhiệt','Bảo vệ quá tải động cơ; cần xác nhận dải chỉnh và thiết bị chủ.'),
        (r'CTT|LC1|\bMC |NXC|CJX','Khởi động từ','Đóng cắt tải qua cuộn điều khiển; cần xác nhận điện áp cuộn hút.'),
        (r'AUX|UA-1','Tiếp điểm phụ','Phụ kiện báo trạng thái; cần xác nhận thiết bị tương thích.'),
        (r'ACB|NW\d','ACB','Đóng cắt và bảo vệ lộ nguồn; cần xác nhận bộ bảo vệ và cấu hình.'),
        (r'RCBO|32KGR|RKP','RCBO','Bảo vệ quá dòng và dòng rò theo mã thực tế.'),
        (r'RCCB|BS32|RKN','Thiết bị chống rò','Cần xác nhận loại bảo vệ và phối hợp bảo vệ quá dòng.'),
        (r'MCB|NXB|BKN|BKH','MCB','Bảo vệ quá dòng theo mã, số cực và khả năng cắt thực tế.'),
        (r'NZ7|ATS','ATS','Chuyển nguồn theo sơ đồ và cấu hình thực tế.'),
        (r'BKD|\bINS ','Cầu dao cách ly','Cách ly nguồn theo cấu hình thực tế.'),
    ]:
        if re.search(pattern,n):return kind,use
    return 'CAD thiết bị theo nhãn nguồn','Tham khảo hình học; xác nhận chức năng, mã thiết bị và thông số trước thiết kế.'
def effective_name(doc,name):
    seen=set()
    while name.startswith('*U') and name not in seen:
        seen.add(name)
        try:
            tags=doc.blocks.get(name).block_record.get_xdata('AcDbBlockRepBTag')
            handle=next(t.value for t in tags if t.code==1005)
            name=doc.entitydb[handle].dxf.name
        except Exception:break
    return name
def main(brand):
    stem={'LS':'ls','Chint':'chint','Schneider':'schneider'}[brand]
    source=Path('D:/THƯ VIỆN')/('@'+('CHINT' if brand=='Chint' else brand.upper())+'.dwg')
    dxf=BASE/('tmp/brand_update/ls.dxf' if brand=='LS' else f'tmp/multibrand/{stem}.dxf')
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    doc=ezdxf.readfile(dxf); refs=list(doc.modelspace().query('INSERT'))
    previous=ROOT/brand/'kiem_tra_nguon_bo_sung.json'
    report={'source':str(source),'sha256':source_hash,'dxf_units':doc.units,'source_insert_count':len(refs),'added':read(previous)['added'] if previous.exists() else [],'duplicates':[],'unidentified':[],'empty':[]}
    print(brand,'source loaded',flush=True)
    existing={}
    cache=BASE/'tmp/brand_update/existing_geometry_v2.json'
    if cache.exists():existing=read(cache)
    else:
        for p in ROOT.glob('*/ThietBi/*/CadDon/*/ban_ve.dxf'):
            try:
                d=ezdxf.readfile(p);k=fingerprint(list(visible(d,d.modelspace())))
                if k:existing.setdefault(k,[]).append(p.relative_to(ROOT).as_posix())
            except Exception:continue
        save(cache,existing)
    seen={};named=collections.defaultdict(list)
    for e in refs:named[effective_name(doc,e.dxf.name)].append(e)
    for name,occurrences in named.items():
        if not relevant(brand,name):
            report['unidentified'].append({'block':name,'count':len(occurrences),'status':'Not assigned to this brand from block name; retained in source'})
            continue
        for e in occurrences:
            # A project can reuse a library state at many positions, scales and
            # rotations. Index the saved block state once in native coordinates.
            native=e.copy()
            native.dxf.insert=(0,0,0)
            native.dxf.rotation=0
            native.dxf.xscale=native.dxf.yscale=native.dxf.zscale=1
            es=list(visible(doc,[native]));k=fingerprint(es)
            if not k:
                report['empty'].append({'block':name,'handle':e.dxf.handle});continue
            if k in seen:continue
            seen[k]=name
            provenance={'file':str(source),'sha256':source_hash,'block':name,'saved_block':e.dxf.name,'handle':e.dxf.handle,'geometry_key':k,'units':doc.units,'instance_transform':{'insert':list(e.dxf.insert),'rotation':e.dxf.rotation,'scale':[e.dxf.xscale,e.dxf.yscale,e.dxf.zscale]},'state_basis':'Saved block state in native coordinates; project insertion position/rotation/scale omitted, invisible entities and off/frozen layers omitted; dynamic state not independently confirmed'}
            matches=[path for path in existing.get(k,[]) if (ROOT/path).exists() and file_units(ROOT/path)==doc.units]
            if matches:
                report['duplicates'].append({'source':provenance,'existing':matches});continue
            ident='SRC_'+stem.upper()+'_'+k[:12];folder=ROOT/brand/'ThietBi'/ident
            view=folder/'HinhChieu'/ident;view.mkdir(parents=True,exist_ok=True)
            b=bbox.extents(es,fast=True);out=ezdxf.new('R2018');out.units=doc.units
            importer=Importer(doc,out);importer.import_entities(es,out.modelspace());importer.finalize()
            out.modelspace().delete_all_entities() if not len(out.modelspace()) else None
            for v in out.modelspace():v.translate(-b.center.x,-b.center.y,-b.center.z)
            check=bbox.extents(out.modelspace(),fast=True)
            assert check.has_data and abs(check.size.x-b.size.x)<0.001 and abs(check.size.y-b.size.y)<0.001, name
            out.saveas(view/'ban_ve.dxf')
            backend=SVGBackend();Frontend(RenderContext(out),backend).draw_layout(out.modelspace(),layout_properties=LayoutProperties('Model','#212830','#ffffff',units=out.units,dark_background=True))
            preview_svg=re.sub(r'(stroke-width: )(\d+)',lambda m:m[1]+str(max(1500,int(m[2]))),backend.get_string(Page(0,0)))
            (view/'xem_truoc.svg').write_text(preview_svg,encoding='utf-8')
            face='Chưa xác nhận hướng nhìn';kind,use=purpose(name);title=f'{brand} · {name} · CAD nguồn'
            record={'id':ident,'thiet_bi':ident,'loai_hinh':'block','ten_hinh':name,'tep':{'cad_dxf':'ban_ve.dxf','preview':'xem_truoc.svg'},'kich_thuoc_hinh_mm':{'ngang':round(b.size.x,3),'cao':round(b.size.y,3)} if out.units==4 else None,'kich_thuoc_don_vi_nguon':{'ngang':round(b.size.x,3),'cao':round(b.size.y,3),'INSUNITS':out.units},'nguon':provenance,'source_state_verified':False}
            save(view/'thong_tin.json',record)
            placement={'cho_phep_chen':False,'huong_dan':'Xác nhận mã, mặt, trạng thái CAD và đơn vị trước khi chèn.'}
            metadata={'id_hinh_goc':ident,'huong_nhin':face,'tep':record['tep'],'bo_tri_trong_tu':placement,'nhan_dien_mat':{'verified':False},'nguon':provenance,'ghi_chu':'Giữ số tọa độ và đơn vị nguồn; không tự đổi inch/không đơn vị thành mm.'}
            for dest in [folder/'CadDon'/ident,folder/'CadChenTu']:
                dest.mkdir(parents=True,exist_ok=True)
                for f in ['ban_ve.dxf','xem_truoc.svg']:shutil.copy2(view/f,dest/f)
                save(dest/'thong_tin_cad_chen.json',metadata)
            profile={'nhom':brand,'ten_kieu':title,'ten_san_pham':title,'ban_chat':kind,'cong_dung':use,'vi_tri_lap_dat':'Chưa xác nhận kiểu gá và tư thế lắp.','hang_xac_nhan':None,'ma_dong_san_pham':None,'thong_so':{'nhan_block_nguon':name,'dong_dinh_muc_A':None,'dien_ap_V':None},'tu_khoa_tim_kiem':[name,brand,kind],'muc_do_xac_nhan':'CAD tham khảo từ file thư viện hãng; nhãn nguồn chưa xác nhận mã đặt hàng, hãng của từng block, hướng nhìn và thông số điện.','nguon_tham_khao':[],'nguon_cad':provenance,'cac_hinh_cad':[ident],'auto_select':False,'needs_review':True,'yeu_cau_chon_day':{'tiet_dien_mac_dinh_mm2':None,'quy_tac':'Xác định từng cọc, dòng, điện áp và giới hạn dây theo mã thực tế.'},'yeu_cau_lap_dat':{'status':'Chưa xác nhận dữ liệu hãng','unknown_value':None,'cad_rotation_is_mounting_approval':False},'cad_don':[{'id_hinh_goc':ident,'huong_nhin':face,'nhan_hien_thi':name,'bo_tri_trong_tu':placement,'duong_dan':f'CadDon/{ident}/ban_ve.dxf'}],'cad_chen_tu':{'id_hinh_goc':ident,'huong_nhin':face,'duong_dan':'CadChenTu/ban_ve.dxf'}}
            save(folder/'thong_tin_thiet_bi.json',profile)
            existing[k]=[(folder/'CadDon'/ident/'ban_ve.dxf').relative_to(ROOT).as_posix()]
            report['added'].append({'id':ident,'block':name,'profile':(folder/'thong_tin_thiet_bi.json').relative_to(ROOT).as_posix(),'units':out.units})
    save(cache,existing);save(ROOT/brand/'kiem_tra_nguon_bo_sung.json',report)
    print(brand,'added',len(report['added']),'duplicates',len(report['duplicates']),'unclassified block names',len(report['unidentified']),flush=True)
if __name__=='__main__':main(sys.argv[1])

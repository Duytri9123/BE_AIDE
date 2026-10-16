"""Turn source CAD into browsable information profiles, retaining provenance and duplicates."""
import hashlib,json,re,shutil
from collections import Counter
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import ezdxf
from ezdxf.lldxf.tagwriter import TagCollector
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page
from ezdxf.addons.drawing.config import Configuration
from ezdxf.addons.drawing.properties import LayoutProperties

ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB'
LABELS={'CT':'Biến dòng','TERMINAL_BLOCK':'Cầu đấu','TERMINAL_STOP':'Chặn cầu đấu',
        'LIGHT':'Đèn báo','PUSHBUTTON':'Nút nhấn','SELECTOR_SWITCH':'Công tắc chọn',
        'CONTACTOR':'Contactor','FUSE_HOLDER':'Đế cầu chì','FUSE':'Cầu chì',
        'IO_MODULE':'Mô-đun I/O','PLC':'Bộ điều khiển PLC','DDC':'Bộ điều khiển DDC',
        'METER':'Đồng hồ đo điện','SELECTOR_METER':'Chuyển mạch đo','CAPACITOR':'Tụ bù',
        'REACTOR':'Cuộn kháng','FAN':'Quạt tủ điện','FILTER':'Lưới lọc/thông gió',
        'VENT_HOOD':'Chụp che quạt','INSULATING_SUPPORT':'Giá đỡ/phíp cách điện',
        'NAMEPLATE':'Nhãn tủ điện','FIRE_SUPPRESSION_REFERENCE':'Quả cầu chữa cháy','BUZZER':'Còi báo',
        'ENCLOSURE_REFERENCE':'Bản vẽ vỏ tủ','SOURCE_REFERENCE':'Bản vẽ tổng hợp'}


def infer(row):
    i=row['index'];name=row['name'];text=' '.join([name,*row.get('texts',[])]).upper()
    group=Path(row['path']).parts[0]
    if group=='Form tủ':return 'ENCLOSURE_REFERENCE'
    if i==125:return 'REACTOR'
    if '6 KG' in text or 'CHỮA CHÁY' in text or i in {122,126,128,129}:return 'FIRE_SUPPRESSION_REFERENCE'
    if group=='BienDong':return 'CT'
    if group=='Cuộn kháng':return 'REACTOR'
    if group=='Cầu đấu':return 'TERMINAL_STOP' if re.search(r'CHAN TER|END BRA',text) else 'TERMINAL_BLOCK'
    if group=='Phíp':return 'INSULATING_SUPPORT'
    if group=='Tụ bù':return 'CAPACITOR'
    if group=='Quạt':
        if i==449:return 'VENT_HOOD'
        if 455<=i<=486 and i not in {470}:return 'VENT_HOOD'
        if i in {470,487}:return 'VENT_HOOD'
        if '.300' in text or re.search(r'LƯỚI|TẤM LỌC|TẤM CHE|Q_TAM|\bFILTER\b',text) or i in {512,513}:return 'FILTER'
        if 'FKL' in text or re.search(r'\bFAN\b|QUẠT',text):return 'FAN'
        return 'FILTER'
    if group=='ThietBiDoLuongHienThi':
        return 'SELECTOR_METER' if i in {542,543,547,553,561} else 'METER'
    if group=='DenBaoNutNhanCauChiContactor':
        if i==375 or 'BUZZER' in text:return 'BUZZER'
        if 322<=i<=342:return 'NAMEPLATE'
        if i in {351,384}:return 'DDC'
        if i in {352,353,354,355,382,397,402,403}:return 'IO_MODULE'
        if re.search(r'S7-1200|\bLOGO\b',text) or i in {409}:return 'PLC'
        if i in {365,366,378}:return 'TERMINAL_STOP'
        if i in {361,362,363,364,373,380,395,396,405,412,415} or re.search(r'MC\s*\d',text):return 'CONTACTOR'
        if i in {387}:return 'FUSE'
        if i in {391,414,416} or re.search(r'RT-?32|CẦU CHÌ',text):return 'FUSE_HOLDER'
        if i in {367,370,374,379,386,388,389,398,408,411} or 'SELECTOR' in text:return 'SELECTOR_SWITCH'
        if i in {369,375,376,377,385,394,400,401,404,410,413} or 'EMERGENCY STOP' in text:return 'PUSHBUTTON'
        if i in {343,368,371,372,383,390,392,393,399,406} or 'PILOT LIGHT' in text:return 'LIGHT'
        return 'SOURCE_REFERENCE'
    return 'SOURCE_REFERENCE'


def models(row):
    text=' '.join([row['name'],*row.get('texts',[])])
    patterns=[r'\bZCT[- ]?(?:D)?\d+S?\b',r'\bMSQ[- ]?\d+\b',r'\bRCT[- ]?\d+\b',
              r'\bCML\s*\d+A?\b',r'\bKDE\s*\d+A?\b',r'\bEM4H\d+\b',r'\bCV1[34]\d\b',
              r'\bMV-3Tb\b',r'\bPM(?:2220|710)\b',r'\bHYT[- ]?\d+\b',r'\bUK3N\b',
              r'\bCTS\d+\b',r'\b(?:CD|TB)[_-]\d+P[-_]\d+A\b',r'\bFKL\d+(?:[.]\d+)?\b',
              r'\bRT(?:18|36)[- ]\d+(?:\(NT\d+\))?\b',r'\bRT-32A\b',r'\bNP2\b',
              r'\bS7-1200\b',r'\bLOGO\b',r'\bIQ4\b',r'\b(?:16DI|8UI|8AO|8DO)\b',
              r'\bJSJ[- ]?\d+(?:-\dP)?\b',r'\bH&T\s*10D3\b']
    return list(dict.fromkeys(m.group(0).strip() for pattern in patterns for m in re.finditer(pattern,text,re.I)))[:40]


def source_brand(row):
    text=' '.join([row['name'],*row.get('texts',[])]).upper()
    found=[brand for token,brand in [('MIKRO','Mikro'),('MORELE','Morele'),('ANDELI','Andeli'),
            ('NUINTEK','Nuintek'),('SAMWHA','Samwha'),('SHAMWHA','Samwha'),('EMIC','EMIC'),
            ('HOLLEY','Holley'),('IDEC','IDEC'),('CHINT','CHINT'),('SCHNEIDER','Schneider Electric'),
            ('SIEMENS','Siemens'),('RISESUN','RISESUN'),('OMEGA','Omega'),('KACON','KACON'),
            ('LEIPOLE','Leipole'),('LIGHTSTAR','LightStar'),('MITEX','MITEX'),('LS','LS Electric')]
            if re.search(r'(?<![A-Z])'+token+r'(?![A-Z])',text)]
    return list(dict.fromkeys(found))


def fingerprint(doc):
    # Do not deduplicate by appearance or names. Entity tags include coordinates,
    # text and reachable block contents; only storage IDs and display styling differ.
    from ezdxf.disassemble import recursive_decompose
    from ezdxf import bbox
    entities=list(recursive_decompose(doc.modelspace()))
    extent=bbox.extents(entities,fast=True)
    origin=extent.extmin if extent.has_data else (0,0,0)
    records=[]
    for entity in entities:
        clone=entity.copy()
        try:clone.translate(-origin[0],-origin[1],-origin[2])
        except (AttributeError,NotImplementedError):pass
        def value(v):
            if isinstance(v,float):return round(v,5)
            if v.__class__.__name__ in {'Vec2','Vec3'}:return [round(n,5) for n in v]
            return str(v)
        tags=[(t.code,value(t.value)) for t in TagCollector.dxftags(clone) if t.code not in {5,105,330,360,8,62,420,430,347}]
        records.append(json.dumps(tags,ensure_ascii=False))
    return hashlib.sha256(json.dumps(sorted(records)).encode()).hexdigest()


def main():
    rows=json.loads((ROOT/'outputs/source-630-review/inventory.json').read_text(encoding='utf8'))
    manifest_path=CAT/'ai_library_manifest.json'
    backup=ROOT/'outputs/source-630-before-processing.zip'
    if not backup.exists():
        with ZipFile(backup,'w',ZIP_DEFLATED) as z:
            z.write(manifest_path,'ai_library_manifest.json')
    manifest=json.loads(manifest_path.read_text(encoding='utf8'))
    seen={};results=[];created=[]
    for row in rows:
        path=CAT/row['path'];typ=infer(row);code=models(row)
        report=dict(index=row['index'],source=row['path'],name=row['name'],category=typ,
                    source_models=code,price='---',texts=row.get('texts',[]),source_sha256=row['sha256'])
        if row.get('archive_only'):
            report.update(status='processed_native_library_archive',note='Tệp DWG thư viện tổng; các thành phần DXF đã được kiểm kê riêng.')
            results.append(report);continue
        if not row.get('entity_counts'):
            report.update(status='processed_empty_legacy_reference',note='Bản form rỗng; giữ thông tin kích thước trong hồ sơ nguồn, không đưa CAD rỗng vào chọn thiết bị.')
            results.append(report);continue
        doc=ezdxf.readfile(path);fp=fingerprint(doc)
        if fp in seen:
            report.update(status='processed_duplicate_geometry',profile=seen[fp],geometry_sha256=fp)
            results.append(report);continue
        folder=Path(row['path']).parts[0]
        dest=CAT/folder/'ThietBi'/('SOURCE_'+hashlib.sha1(row['path'].encode()).hexdigest()[:16])
        dest.mkdir(exist_ok=True,parents=True)
        view_id='SOURCE-'+hashlib.sha1(row['path'].encode()).hexdigest()[:16]
        target=dest/'CadDon'/view_id;target.mkdir(exist_ok=True,parents=True)
        shutil.copyfile(path,target/'ban_ve.dxf')
        preview=CAT/row['preview_path'] if row.get('preview_path') else None
        if preview and preview.is_file():shutil.copyfile(preview,target/'xem_truoc.svg')
        else:
            backend=SVGBackend()
            Frontend(RenderContext(doc),backend,config=Configuration()).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#212930','#ffffff',units=4,dark_background=True))
            (target/'xem_truoc.svg').write_text(backend.get_string(Page(0,0)),encoding='utf8')
        multi=row['metadata'].get('loai_hinh') in {'group','region'}
        source_name=row['name']
        opaque=source_name.startswith(('*','A$C','Hình CAD chưa','Hình rời')) or source_name in {'bbbb','hhhhh','HGHGH','dfwf','GVFDXBG','BGVFG'} or '/' in source_name
        title=LABELS[typ]+' · '+(' / '.join(code[:3]) if code else f"mẫu nguồn {row['index']}") if opaque else LABELS[typ]+' · '+source_name
        specs={'Loại thiết bị':LABELS[typ],'Phạm vi bản vẽ':'Cụm/bảng nhiều thành phần' if multi else 'Hình chiếu/chi tiết nguồn',
               'Mã/dòng trên nguồn':' / '.join(code) or source_name,'Giá':'---'}
        ratings=list(dict.fromkeys(re.findall(r'\b\d+(?:[.,]\d+)?\s*(?:/\s*\d+\s*)?(?:VAC|VDC|kVAr|kvar|kVA|Hz|kA|A|V|mm2|mm²)\b',' '.join(row.get('texts',[])),re.I)))[:20]
        if ratings:specs['Nhãn thông số đọc từ nguồn']='; '.join(ratings)
        brands=source_brand(row)
        info=dict(nhom=folder,ten_kieu=source_name,ten_san_pham=title,ban_chat=typ,
                  ma_dong_san_pham=' / '.join(code) or None,hang_xac_nhan=brands[0] if len(brands)==1 else None,
                  thong_so=specs,cong_dung=LABELS[typ]+' dùng để tra cứu thông tin, chọn mã và bố trí theo mẫu CAD tham khảo.',
                  nhan_dien_ai=dict(loai_thiet_bi_code='ASSEMBLY_REFERENCE' if multi else typ,
                                   source_component_type=typ,cac_ma_dong_san_pham=code,
                                   fabrication_ready=False,generic_shape=not bool(code)),
                  auto_select=False,needs_review=True,
                  source_catalog_review=dict(source_path=row['path'],source_sha256=row['sha256'],
                                             texts=row.get('texts',[]),component_type=typ,contains_multiple_components=multi,
                                             status='information_catalogued',visual_review='category_contact_sheet_2026_10_16'),
                  nguon_cad=dict(file=row['path'],block=source_name,sha256=row['sha256']),
                  tu_khoa_tim_kiem=[LABELS[typ],source_name,*code],
                  cad_don=[dict(id_hinh_goc=view_id,huong_nhin='Mặt bên' if re.search(r'SIDE|CẠNH|MẶT HÔNG|MH\b',source_name,re.I) else 'Mặt trước' if re.search(r'FRONT|FONT|MẶT TRƯỚC|MT\b',source_name,re.I) else 'Mặt trên' if re.search(r'TOP|MẶT BẰNG|ĐỈNH|\bMB\b',source_name,re.I) else 'Chưa xác nhận hướng nhìn',
                                duong_dan=f'CadDon/{view_id}/ban_ve.dxf',bo_tri_trong_tu={'cho_phep_chen':False})],
                  cad_chen_tu={'id_hinh_goc':view_id},
                  gia_ban={'don_gia':'---','don_vi_tien_te':'VND','trang_thai':'Không yêu cầu giá'})
        profile=dest/'thong_tin_thiet_bi.json'
        profile.write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        relative=profile.relative_to(CAT).as_posix();seen[fp]=relative;created.append(relative)
        report.update(status='processed_information_profile',profile=relative,geometry_sha256=fp)
        results.append(report)
        if len(results)%50==0:print('Processed',len(results),flush=True)
    by_path={r['source']:r for r in results}
    for source in manifest['source_cad_documents']:
        review=by_path[source['path']]
        source.update(status=review['status'],category=review['category'],information_profile=review.get('profile'),
                      source_models=review['source_models'],price='---',auto_select=False,insertable=False)
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    summary=dict(total_sources=len(results),new_information_profiles=len(created),statuses=dict(Counter(r['status'] for r in results)),
                 categories=dict(Counter(r['category'] for r in results)),pending_sources=0)
    (ROOT/'docs/source-630-catalog-processing.json').write_text(json.dumps(dict(summary=summary,items=results),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':main()

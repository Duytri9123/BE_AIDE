"""Retain complete, placed LS references from the supplied accessory DWG."""
import json,logging,re,shutil
from pathlib import Path
import ezdxf
from ezdxf import bbox,transform,xref
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page
from ezdxf.addons.drawing.properties import LayoutProperties
logging.disable(logging.CRITICAL)
base=Path(__file__).resolve().parents[1];root=base/'data/CatalogTB'
source=ezdxf.readfile(base/'tmp/accessory_source_review/source.dxf')
report=[]
for handle,frame,title,model in [('37AA6A','100','ABN100AF','ABN'),('37AA75','125','ABH125AF','ABH'),('37AA8D','250','ABN250AF/ABH250AF/ABS250AF','ABN 250c'),('37AA98','400','ABN400AF','ABN 400c'),('37AAA3','800','ABN800AF','ABN 800c'),('37AF4C','1000','ABS 1000','ABS 1000b'),('37AABF','1000','EBS 1000','EBS 1003b')]:
    entity=source.entitydb[handle];attrs={a.dxf.tag:a.dxf.text for a in entity.attribs}
    assert attrs['ORIGIN']=='LS' and attrs['TYPE']==model and attrs['POLES']=='3P/f',attrs
    kind='ELCB' if model.startswith('EBS') else 'MCCB'
    profiles=[p for p in (root/'LS').rglob('thong_tin_thiet_bi.json') if json.loads(p.read_text(encoding='utf-8')).get('ten_san_pham')==f'{kind} LS {title} · 3P']
    assert len(profiles)==1,profiles
    path=profiles[0];data=json.loads(path.read_text(encoding='utf-8'));vid='LS-ORIGINAL-'+handle
    native=path.parent/'HinhChieu'/vid;single=path.parent/'CadDon'/vid
    native.mkdir(exist_ok=True);single.mkdir(exist_ok=True)
    doc=ezdxf.new('R2018');doc.units=4
    # The legacy Importer drops REGION entities. The xref loader retains ACIS
    # regions and the resources of the complete device reference.
    xref.load_modelspace(source,doc,filter_fn=lambda e:e.dxf.handle==handle)
    # No layer, color, conductor or component deletion. Keep the original INSERT.
    doc.saveas(native/'ban_ve.dxf')
    ext=bbox.extents(doc.modelspace(),fast=True);assert ext.has_data
    source_types=[(e.dxftype(),e.dxf.get('color',256)) for e in source.blocks[entity.dxf.name]]
    target_insert=next(e for e in doc.modelspace() if e.dxftype()=='INSERT')
    target_types=[(e.dxftype(),e.dxf.get('color',256)) for e in doc.blocks[target_insert.dxf.name]]
    assert source_types==target_types
    transform.translate(doc.modelspace(),(-ext.center.x,-ext.center.y,0))
    doc.saveas(single/'ban_ve.dxf')
    backend=SVGBackend();Frontend(RenderContext(doc),backend).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#212830','#ffffff',units=4,dark_background=True))
    svg=re.sub(r'(stroke-width: )(\d+)',lambda m:m[1]+str(max(1500,int(m[2]))),backend.get_string(Page(0,0)))
    (single/'xem_truoc.svg').write_text(svg,encoding='utf-8');shutil.copy2(single/'xem_truoc.svg',native/'xem_truoc.svg')
    label=f'Mặt trước · {model} · {attrs["RATE"]}'
    meta={'id':vid,'loai_hinh':'block','ten_hinh':'Mặt trước','nhan_hien_thi':label,'tep':{'cad_dxf':'ban_ve.dxf','preview':'xem_truoc.svg'},'kich_thuoc_hinh_mm':{'ngang':round(ext.size.x,2),'cao':round(ext.size.y,2)},'source_dwg':'THƯ VIỆN PHỤ KIỆN( Mới nhất).dwg','source_handle':handle,'source_attributes':attrs}
    (native/'thong_tin.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    placement={'mat_form_mac_dinh':'Mặt trước','cho_phep_chen':False,'huong_dan':'Bản CAD nguồn có đồng/đầu nối tích hợp. Đối chiếu cấu hình, đầu nối và thông số trước khi dùng cho thi công.'}
    insert={'id_hinh_goc':vid,'huong_nhin':'Mặt trước','nhan_hien_thi':label,'tep':meta['tep'],'bo_tri_trong_tu':placement,'ghi_chu':'Giữ nguyên block nguồn và toàn bộ đồng/đầu nối; chỉ dịch điểm chèn về tâm hình.'}
    (single/'thong_tin_cad_chen.json').write_text(json.dumps(insert,ensure_ascii=False,indent=2),encoding='utf-8')
    if vid not in data['cac_hinh_cad']:data['cac_hinh_cad'].append(vid)
    data['cad_don']=[v for v in data['cad_don'] if v['id_hinh_goc']!=vid]+[{'id_hinh_goc':vid,'huong_nhin':'Mặt trước','nhan_hien_thi':label,'bo_tri_trong_tu':placement,'duong_dan':f'CadDon/{vid}/ban_ve.dxf'}]
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    report.append({'profile':str(path.relative_to(root)),'view':vid,'source_attributes':attrs,'block_entities_preserved':len(source_types)})
    print(vid,attrs,flush=True)
(root/'LS/kiem_tra_khoi_dong_dau_noi_goc.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

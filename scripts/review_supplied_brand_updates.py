"""Verify source-reference assets and create contact sheets for visual review."""
import io,json,math,hashlib,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import cairosvg,ezdxf
from ezdxf import bbox
BASE=Path(__file__).resolve().parents[1];ROOT=BASE/'data/CatalogTB'
brand=sys.argv[1];report_path=ROOT/brand/'kiem_tra_nguon_bo_sung.json'
report=json.loads(report_path.read_text(encoding='utf-8'));items=report['added']
dest=BASE/'tmp/brand_update/review'/brand;dest.mkdir(parents=True,exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12)
pages=[];canvas=None
for i,item in enumerate(items):
    p=ROOT/item['profile'];profile=json.loads(p.read_text(encoding='utf-8'));folder=p.parent;ident=item['id']
    assert profile['auto_select'] is False and profile['needs_review'] is True
    assert profile['hang_xac_nhan'] is None and profile['ma_dong_san_pham'] is None
    source=folder/'HinhChieu'/ident;record=json.loads((source/'thong_tin.json').read_text(encoding='utf-8'))
    doc=ezdxf.readfile(source/'ban_ve.dxf');box=bbox.extents(doc.modelspace(),fast=True)
    assert len(doc.modelspace())>0 and box.has_data and doc.units==item['units']
    expected=record['kich_thuoc_don_vi_nguon'];assert abs(box.size.x-expected['ngang'])<.0011 and abs(box.size.y-expected['cao'])<.0011
    sha=hashlib.sha256((source/'ban_ve.dxf').read_bytes()).hexdigest()
    for view in [folder/'CadDon'/ident,folder/'CadChenTu']:
        assert sha==hashlib.sha256((view/'ban_ve.dxf').read_bytes()).hexdigest()
        metadata=json.loads((view/'thong_tin_cad_chen.json').read_text(encoding='utf-8'))
        assert metadata['bo_tri_trong_tu']['cho_phep_chen'] is False
    image=Image.open(io.BytesIO(cairosvg.svg2png(url=str(source/'xem_truoc.svg'),output_width=190,output_height=210))).convert('RGBA')
    if i%24==0:canvas=Image.new('RGB',(1200,1120),'white');draw=ImageDraw.Draw(canvas)
    x=(i%6)*200;y=((i%24)//6)*280
    canvas.paste(image,(x+5,y+5),image)
    draw.text((x+5,y+219),str(i+1)+' '+item['block'][:28],font=font,fill='black')
    draw.text((x+5,y+236),item['block'][28:56],font=font,fill='black')
    draw.text((x+5,y+253),ident[-12:],font=font,fill='black')
    if i%24==23 or i==len(items)-1:
        file=dest/f'page_{len(pages)+1:02}.png';canvas.save(file);pages.append(str(file.resolve()))
report['verification']={'asset_count':len(items),'nonempty_geometry':True,'source_coordinate_size_preserved':True,'insertion_copies_identical':True,'units_preserved':True,'auto_select':False,'insertion_allowed':False,'contact_sheets':pages,'visual_review_completed':False}
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(brand,'verified',len(items),'assets;',len(pages),'contact sheets',flush=True)

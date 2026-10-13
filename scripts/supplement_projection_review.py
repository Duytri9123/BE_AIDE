"""Apply individually reviewed projections; keep original CAD bytes and evidence."""
import hashlib,json,re
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
ROOT=BASE/'data/CatalogTB'
OUT=BASE.parent/'outputs/catalogtb-projection-review'
rows=json.loads((OUT/'evidence.json').read_text(encoding='utf8'))
def save(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

# Each number refers to an inspected card in evidence.json and sheet-NN.png.
# Do not replace these decisions with a name/rectangle heuristic.
decisions={}
def assign(face,numbers):
    for number in numbers:
        assert number not in decisions,number
        decisions[number]=face
assign('Mặt trước',[8,9,13,15,16,17,18,24,26,27,30,31,33,35,36,
 65,66,67,69,74,77,80,83,84,85,86,
 142,148,149,150,151,153,155,156,161,165,168,169,170,172,174,176,
 177,179,180,181,182,184,185,188,190,195,197,199,201,202,204,205,206,207,208,
 211,215,221,223,224,226,230,231,233,235,238,239,242,243,247,250,251,254,255,
 257,259,260,261,264,269,271,272,273,276,278,279,281,286,287,288,292,294,
 296,298,301,307,311,313])
assign('Mặt bên',[12,14,19,20,21,22,23,25,28,29,32,
 68,70,71,75,82,88,140,141,144,154,159,162,167,183,187,191,
 198,200,203,210,218,219,227,228,234,236,240,244,245,246,256,258,263,
 267,268,270,274,277,282,283,284,291,293,297,299,300,306,309,310,312])
assign('Mặt trên',[146,157,158,166,173,175,193,222,229,237,252,253,262,265,
 285,295,303,308])
assign('Lỗ khoét cánh',[143,145,152,164,171,178,186,192,194,196,209,212,213,
 214,216,217,220,248,249,266,275,280,289,290,302,304,305])
assign('Nắp che mặt trước',[225])
review=[]
for row in rows:
    number=row['number']
    if number not in decisions:continue
    p=ROOT/row['profile'];d=json.loads(p.read_text(encoding='utf8'))
    entry=next(v for v in d['cad_don'] if v['id_hinh_goc']==row['view'])
    old=entry.get('huong_nhin')
    # Already explicit labels are retained with their state/rating annotations.
    if old not in ('Chưa xác nhận hướng nhìn','Chưa xác định hướng nhìn'):
        if (entry.get('nhan_dien_mat') or {}).get('method')=='individual_visual_review':
            review.append({'profile':row['profile'],'view':row['view'],**entry['nhan_dien_mat']})
        continue
    face=decisions[number]
    proof={'review_date':'2026-10-11','method':'individual_visual_review',
      'evidence_card':number,'evidence_image':str((OUT/row['image']).relative_to(BASE.parent)),
      'previous_label':old,'projection':face,
      'basis':'Device controls/terminals and relative projection geometry; source block label used only when consistent with the inspected image.',
      'mounting_orientation_verified':False,'exact_sku_verified':False}
    entry['huong_nhin']=face;entry['nhan_dien_mat']=proof
    if face=='Lỗ khoét cánh':
        entry['asset_role']='door_cutout'
        entry.setdefault('bo_tri_trong_tu',{})['cho_phep_chen']=False
    primary=(d.get('cad_chen_tu') or {}).get('id_hinh_goc')==row['view']
    if primary:d['cad_chen_tu']['huong_nhin']=face
    save(p,d)
    paths=[p.parent/'CadDon'/row['view']/'thong_tin_cad_chen.json',
           p.parent/'HinhChieu'/row['view']/'thong_tin_cad_chen.json']
    if primary:paths.append(p.parent/'CadChenTu/thong_tin_cad_chen.json')
    for metadata in paths:
        if not metadata.is_file():continue
        m=json.loads(metadata.read_text(encoding='utf8'))
        m['huong_nhin']=face;m['nhan_dien_mat']=proof
        if face=='Lỗ khoét cánh':
            m['asset_role']='door_cutout';m.setdefault('bo_tri_trong_tu',{})['cho_phep_chen']=False
        save(metadata,m)
    review.append({'profile':row['profile'],'view':row['view'],**proof})

mx=ROOT/'Bộ điều khiển/ThietBi/BaoVePha_MX100/thong_tin_thiet_bi.json'
d=json.loads(mx.read_text(encoding='utf8'))
url='https://itmikro.com.my/wp-content/uploads/2020/08/mx100-1.pdf'
d.update(ten_kieu='Rơ le bảo vệ pha Mikro MX100',ten_san_pham='Rơ le bảo vệ pha Mikro MX100',
    ban_chat='Rơ le giám sát mất pha và thứ tự pha',
    cong_dung='Giám sát mất pha và sai thứ tự pha của nguồn ba pha.',
    ma_dong_san_pham='MX100',
    muc_do_xac_nhan='Nhận diện họ Mikro MX100 theo nhãn nguồn và bao hình CAD 35 × 80; chưa xác định biến thể điện áp hoặc mã đặt hàng đầy đủ.')
d['nhan_dien_ai']={'loai_thiet_bi_code':'PHASE_RELAY','measurement_function':'phase_sequence_and_phase_failure'}
d['nguon_tham_khao']=[url]
d['tai_lieu_hang']=url
d['nhan_dien_web']={'review_date':'2026-10-11','brand_candidate':'MIKRO',
    'display_name':d['ten_san_pham'],'product_family':'MX100',
    'user_accepts_approximate_family':True,'status':'family_identified_from_source_label_and_dimensions','exact_sku_verified':False,
    'sources':[url],'manufacturer_family_dimensions_mm':{'width':35,'height':80,'depth':72.5},
    'cad_front_dimensions_mm':{'width':35,'height':80},
    'cad_geometry_resized':False,'selected_voltage':None,
    'identification_basis':'Source MX100 label, 35 × 80 CAD envelope, official Mikro two-indicator plug-in relay family.'}
old=d.get('nhan_dien_bo_sung_20261010',{})
old.update(category_code='PHASE_RELAY',superseded_by='nhan_dien_web',
    official_family_sources=[url],limitation='Chưa xác định MX100-230 hay MX100-400; thông số họ không phải cấu hình đã chọn.')
d['tu_khoa_tim_kiem']=['MX100','Mikro MX100','PHASE_RELAY','rơ le mất pha','rơ le thứ tự pha']
# Socket/depth/voltage are not supplied by this one CAD face. Keep insertion pending.
d['auto_select']=False;d['needs_review']=True
save(mx,d)
save(OUT/'applied-face-review.json',review)
print(json.dumps({'individual_face_updates':len(review),'MX100_function':'PHASE_RELAY'}))

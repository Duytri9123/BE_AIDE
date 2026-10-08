"""CAD-source layout review, kept separate from fabrication and exact SKU matching."""
import html
import json
import re
from pathlib import Path

import ezdxf
from ezdxf import bbox
from ezdxf.addons.drawing import Frontend, RenderContext, svg, layout
from ezdxf.addons.drawing.config import Configuration, ColorPolicy, BackgroundPolicy
from ezdxf.enums import TextEntityAlignment

from app.services.cad.catalogtb_assets import resolve, instance_count
from app.services.cad.library_assets import insert_library_asset
from app.services.cad.design_labels import effective_spec, rating_text


def pack_rows(entries, width, gap=12):
    rows=[];row=[];used=0
    for e in entries:
        if e['w'] > width:
            raise ValueError('CAD thiết bị rộng hơn vùng ray khả dụng')
        needed=e['w']+(gap if row else 0)
        if row and used+needed > width:
            rows.append(row);row=[];used=0;needed=e['w']
        row.append(e);used+=needed
    if row:rows.append(row)
    return rows


def balanced_rows(entries, width, gap=0):
    import math
    n=max(1,math.ceil((sum(e['w'] for e in entries)+gap*max(0,len(entries)-1))/width))
    while n<=max(1,len(entries)):
        rows=[[] for _ in range(n)];used=[0.]*n
        for e in entries:
            eligible=[i for i in range(n) if used[i]+e['w']+(gap if rows[i] else 0)<=width]
            if not eligible:break
            i=min(eligible,key=lambda i:used[i]);used[i]+=e['w']+(gap if rows[i] else 0);rows[i].append(e)
        else:return [row for row in rows if row]
        n+=1
    raise ValueError('CAD thiết bị không vừa chiều rộng ray')


def generate(devices, dimensions, output_dir, panel_code='TĐT', distribution_method=None, branch_arrangement=None, original_dimensions=None):
    if panel_code != 'TĐT':
        raise ValueError('Bản rà soát này dành riêng cho TĐT; cần bộ bố trí cho loại tủ khác')
    declared={d.get('cad',{}).get('distribution_method') for d in devices if d.get('cad',{}).get('distribution_method')}
    if len(declared)>1:raise ValueError('Có phương án phân phối nguồn mâu thuẫn')
    if not distribution_method and declared:distribution_method=next(iter(declared))
    arrangement={d.get('cad',{}).get('branch_arrangement') for d in devices if d.get('cad',{}).get('branch_arrangement')}
    if len(arrangement)>1:raise ValueError('Bố trí nhánh mâu thuẫn')
    if not branch_arrangement and arrangement:branch_arrangement=next(iter(arrangement))
    rules=json.loads((Path(__file__).resolve().parents[3]/'data/design_rules/fishbone_rstn.json').read_text(encoding='utf8'))
    pitch=rules['layout_assumptions_mm']['spine_pitch']
    height,width,depth=map(float,dimensions)
    doc=ezdxf.new('R2010');doc.units=4;m=doc.modelspace()
    for name,color in [('CABINET',7),('CAD_DEVICE',7),('REVIEW',30),('LABEL',7),('DEVICE_LABEL',7),('PLAN_R',1),('PLAN_S',2),('PLAN_T',5),('PLAN_N',8)]:
        doc.layers.new(name,dxfattribs={'color':color})
    def box(x,y,w,h,review=False):
        m.add_lwpolyline([(x,y),(x+w,y),(x+w,y+h),(x,y+h)],close=True,
                        dxfattribs={'layer':'REVIEW' if review else 'CABINET'})
    def label(x,y,s,size=10):
        m.add_text(s,dxfattribs={'height':size,'insert':(x,y),'layer':'LABEL'})
    offset=width+160
    from app.services.cad.source_form_faces import insert_faces
    enclosure_source = insert_faces(m, dimensions, offset)
    if enclosure_source:
        offset = enclosure_source['interior_offset']
    else:
        box(0,0,width,height);box(offset,0,width,height)
        label(0,height+45,'CANH TU',18)
        label(offset,height+45,'MAT TRONG',18)
    entries=[];missing=[];placements=[]
    for d in devices:
        asset_id=(d.get('cad') or {}).get('asset_id')
        if not asset_id:
            missing.append(d.get('tag') or d.get('name'));continue
        asset=resolve(asset_id,'front')
        source=ezdxf.readfile(asset['path'])
        if source.units != 4:
            raise ValueError('CAD nguồn chưa xác nhận đơn vị mm; không tự đổi tỷ lệ')
        bounds=bbox.extents(source.modelspace())
        if not bounds.has_data:raise ValueError('CAD nguồn không có hình học')
        for i in range(instance_count(d.get('quantity') or 1,asset)):
            tag=d.get('tag') or d.get('name')
            if d.get('category')=='LIGHT' and d.get('quantity')==3:
                tag=['R','Y','B'][i]
            rotation=(d.get('cad') or {}).get('review_rotation',0)
            if branch_arrangement=='two_vertical_banks' and d['category']=='N':rotation=0
            if branch_arrangement=='two_vertical_banks' and d['category'] in ('MCB','RCBO','RCCB'):rotation=90
            if rotation not in (0,90) or (rotation and d['category'] not in ('PE','N') and not (branch_arrangement=='two_vertical_banks' and d['category'] in ('MCB','RCBO','RCCB'))):
                raise ValueError('Tư thế CAD chưa được hỗ trợ để rà soát')
            entries.append(dict(device=d,asset=asset,tag=tag,
                w=bounds.size.y if rotation else bounds.size.x,
                h=bounds.size.x if rotation else bounds.size.y,rotation=rotation))
    def place(e,x,y,zone):
        if e.get('fabricated_neutral'):
            box(x,y,e['w'],e['h'],True)
        else:
            insert_library_asset(m,e['asset']['id'],x,y,rotation=e['rotation'])
        config=e['asset'].get('label_config') or {}
        legend=None
        if config.get('enabled'):
            legend=str((e['device'].get('cad') or {}).get('label_text') or config.get('text_template','{tag}')).replace('{tag}',e['tag'])
            if len(legend)>32 or '\n' in legend:
                raise ValueError('Nhãn CAD quá dài; dùng nhãn ngắn theo chức năng')
            m.add_text(legend,dxfattribs={'height':float(config.get('height_mm') or 5),'layer':'DEVICE_LABEL'}).set_placement((x+e['w']/2,y+e['h']+float(config.get('gap_mm') or 8)),align=TextEntityAlignment.MIDDLE_CENTER)
        else:
            if branch_arrangement=='two_vertical_banks' and e['device']['category'] in ('MCB','RCBO','RCCB'):
                pass  # Branch identities and ratings stay in the BOM, not beside crowded CAD terminals.
            else:
                text=e['tag']
                incoming_label=e['device']['category'] in ('MCCB','ACB')
                if incoming_label:
                    text=e['device']['category']+' '+rating_text(e['device'])
                m.add_text(text,dxfattribs={'height':8,'layer':'LABEL'}).set_placement((x+e['w']/2,y+e['h']+12 if incoming_label else y-20),align=TextEntityAlignment.MIDDLE_CENTER)
        placements.append(dict(tag=e['tag'],asset_id=e['asset']['id'],source=e['asset']['profile_path'],
            cad_name=e['asset']['name'],zone=zone,x=x,y=y,w=e['w'],h=e['h'],
            original_spec=e['device'].get('original_spec') or e['device'].get('spec'),selected_spec=effective_spec(e['device']),status='reference_geometry',rotation=e['rotation'],scale=1,
            label_text=legend,replacement_options=e['asset'].get('replacement_options') or {}))
        placements[-1]['physical_units_per_cad']=e['asset'].get('components_per_asset',1)
        if e.get('fabricated_neutral'):
            placements[-1].update(status='custom_fabricated_review',cad_name='Thanh đồng N gia công theo bố trí',length_mm=e['h'],section_mm2=None,source='layout_design',asset_id=None)
    # Door devices are placed on a different physical surface.
    face_mapping=(enclosure_source or {}).get('face_mapping',{})
    doors=[e for e in entries if e['device']['category'] in ('LIGHT','METER','SELECTOR')]
    lights=[e for e in doors if e['device']['category']=='LIGHT']
    total=sum(e['w'] for e in lights)+60*max(0,len(lights)-1);x=(width-total)/2
    def place_on_door(e,x,y):
        face=(e['device'].get('cad') or {}).get('mounting_face') or 'outer_door'
        if face not in ('outer_door','inner_door'):raise ValueError('Mặt lắp thiết bị trên cánh không hợp lệ')
        bounds=(face_mapping.get(face) or {}).get('bounds')
        if enclosure_source and not bounds:raise ValueError('JSON form thiếu mặt cánh đã chọn; không tự đổi sang mặt khác')
        if bounds:
            if x<0 or y<0 or x+e['w']>bounds[2]-bounds[0] or y+e['h']>bounds[3]-bounds[1]:raise ValueError('Thiết bị không vừa mặt cánh đã chọn')
            x+=bounds[0];y+=bounds[1]
        place(e,x,y,face)
        placements[-1]['mounting_face']=face
        placements[-1]['source_face_label']=(face_mapping.get(face) or {}).get('source_label')
    for e in lights:place_on_door(e,x,height-180);x+=e['w']+60
    door_y=height-350
    for e in doors:
        if e['device']['category']=='LIGHT':continue
        place_on_door(e,(width-e['w'])/2,door_y-e['h']);door_y-=e['h']+80
    incoming=[e for e in entries if e['device']['category'] in ('MCCB','ACB')]
    if len(incoming)>1:raise ValueError('Cần phân vùng riêng cho nhiều MCCB/ACB')
    from app.services.cad.design_policy import dimensions_for_current, check_fishbone
    main_rating=rating_text(incoming[0]['device']) if incoming else ''
    main_current=float(main_rating[:-1]) if main_rating else None
    design_policy=dimensions_for_current(main_current)
    if distribution_method=='fabricated_fishbone':check_fishbone(main_current)
    top_gap=design_policy['top_gap_mm'] or 150
    side_margin=design_policy['side_margin_mm'] or 110
    for e in incoming:place(e,offset+(width-e['w'])/2,height-top_gap-e['h'],'interior')
    branch_top=min(height-330,min((p['y']-50 for p in placements if p['tag'] in [v['tag'] for v in incoming]),default=height-330))
    branches=[e for e in entries if e['device']['category'] in ('MCB','RCBO','RCCB')]
    # Descending rated current, then physical width; circuit tags remain identifiers.
    def rating(e):
        value=e['device'].get('in_a')
        if value is None:
            match=re.search(r'(\d+(?:\.\d+)?)\s*A\b',e['device'].get('spec') or '',re.I)
            value=float(match[1]) if match else 0
        return float(value)
    branches.sort(key=lambda e:(-e['w']*e['h'],-rating(e),e['tag']))
    usable=width-140
    if branch_arrangement=='two_vertical_banks':
        rows=[[],[]];used=[0.,0.]
        for e in branches:
            i=min(range(2),key=lambda i:(used[i],len(rows[i]),i));rows[i].append(e);used[i]+=e['h']
        if max(used)>branch_top-160:raise ValueError('Hai dãy dọc không vừa chiều cao tủ theo CAD thực tế')
    elif branch_arrangement=='two_rows_two_banks':
        groups=[[] for _ in range(4)];used=[0.]*4
        for e in branches:
            i=min(range(4),key=lambda i:(used[i],used[i%2]+used[i%2+2],len(groups[i]),i));groups[i].append(e);used[i]+=e['w']
        minimum_width=max(used[0]+used[1],used[2]+used[3])+80+140
        if width<minimum_width:
            raise ValueError(f'Hai hàng / hai nhóm cần rộng ít nhất {minimum_width:g} mm theo biên CAD và vùng bố trí rà soát; không ép vào W{width:g}.')
        rows=groups
    else:rows=balanced_rows(branches,usable,gap=0)
    top=height-340
    for row_index,row in enumerate(rows):
        if branch_arrangement=='two_vertical_banks':
            y=branch_top
            x=offset+side_margin if row_index==0 else offset+width-side_margin-max(e['w'] for e in row)
            for e in row:
                e['rotation']=270 if row_index==0 else 90
                y-=e['h'];place(e,x,y,'interior')
            continue
        if branch_arrangement=='two_rows_two_banks':top=height-340-(row_index//2)*200
        row_h=max(e['h'] for e in row)
        y=top-row_h
        if y < 160:raise ValueError('Thiết bị và vùng đấu cáp không vừa chiều cao tủ')
        if branch_arrangement=='two_rows_two_banks':
            x=offset+70 if row_index%2==0 else offset+width/2+40
            rail_width=width/2-110
        else:x=offset+70;rail_width=usable
        box(x,y+22,rail_width,35,True)
        for e in row:place(e,x,y,'interior');x+=e['w']
        box(offset+70,y-85,usable,40,True)
        top=y-118
    # Proposals only, not generated electrical conductors or ordered material.
    box(offset+20,140,30,height-210,True)
    box(offset+width-50,140,30,height-210,True)
    extras=[e for e in entries if e['device']['category'] in ('PE','N','FUSE_HOLDER','FUSE')]
    if branch_arrangement == 'two_vertical_banks' and distribution_method == 'fabricated_fishbone' and not any(e['device']['category'] == 'N' for e in extras):
        # User-requested fabricated N bar: review envelope, never a claimed catalog SKU.
        extras.append(dict(device={'category': 'N', 'spec': 'Thanh đồng N gia công; tiết diện cần xác nhận'},
                           tag='N', w=10, h=0, rotation=0, fabricated_neutral=True,
                           asset={'id': None, 'profile_path': 'layout_design', 'name': 'Thanh đồng N gia công'}))
    extra_x=offset+70
    for e in extras:
        if e['device']['category'] in ('FUSE_HOLDER','FUSE'):place(e,offset+width-70-e['w'],height-190-e['h'],'interior')
        elif e['device']['category']=='N' and branch_arrangement=='two_vertical_banks':
            if not incoming:raise ValueError('Cần thiết bị nguồn để định vị hệ thanh cái')
            e=dict(e,fabricated_neutral=True,w=rules['layout_assumptions_mm']['neutral_review_width'],h=height-445)
            place(e,offset+width/2+1.5*pitch-e['w']/2,165,'interior')
        else:place(e,extra_x,85,'interior');extra_x+=e['w']+35
    fishbone_connections=[]
    if branch_arrangement=='two_vertical_banks' and branches:
        left_inner=offset+side_margin+max(e['w'] for e in rows[0]) if rows[0] else offset+side_margin
        right_inner=offset+width-side_margin-max(e['w'] for e in rows[1]) if rows[1] else offset+width-side_margin
        route_gap=min(offset+width/2-1.5*pitch-left_inner,right_inner-(offset+width/2+1.5*pitch))-5
        if route_gap<30:raise ValueError(f'Khoảng CB nhánh đến biên thanh cái chỉ {route_gap:g} mm; cần >=30 mm, mục tiêu 40 mm. Phải tăng chiều rộng tủ, không ép thiết bị.')
    else:route_gap=None
    if distribution_method == 'fabricated_fishbone':
        # Electrical topology overlay only. Endpoints deliberately stop outside
        # the imported device: real pole positions must come from a terminal map.
        spines=({'R':offset+width/2-1.5*pitch,'S':offset+width/2-.5*pitch,'T':offset+width/2+.5*pitch,'N':offset+width/2+1.5*pitch}
                if branch_arrangement in ('two_rows_two_banks','two_vertical_banks') else {'R':offset+width-130,'S':offset+width-110,'T':offset+width-90})
        branch_placements=[p for p in placements if p['tag'] in [e['tag'] for e in branches]]
        for phase,spine in spines.items():
            layer='PLAN_'+phase
            m.add_line((spine,165),(spine,height-280),dxfattribs={'layer':layer,'lineweight':35})
            label(spine-5,height-270,phase,9)
            for row_y in ([] if branch_arrangement=='two_vertical_banks' else sorted({p['y']+p['h'] for p in branch_placements})):
                rail_y=row_y+25+('RSTN'.index(phase))*14
                m.add_line((offset+65,rail_y),(spine,rail_y),dxfattribs={'layer':layer,'lineweight':35})
                if branch_arrangement=='two_rows_two_banks':
                    m.add_line((spine,rail_y),(offset+width-65,rail_y),dxfattribs={'layer':layer,'lineweight':35})
        for p in branch_placements:
            d=next(e['device'] for e in branches if e['tag']==p['tag'])
            pole_count=d.get('poles') or (int(re.search(r'(\d)P',d.get('spec') or '').group(1)) if re.search(r'(\d)P',d.get('spec') or '') else None)
            phases=['R','S','T'] if pole_count in (3,4) else [{'R':'R','Y':'S','B':'T','S':'S','T':'T'}.get(str(d.get('phase') or p['tag'].split('/')[-1]).upper())]
            if branch_arrangement=='two_vertical_banks' and pole_count in (2,4):
                phases.append('N')
            for i,phase in enumerate(phases):
                if not phase:continue
                if branch_arrangement=='two_vertical_banks':
                    is_left=p['x']<offset+width/2
                    x=p['x']+p['w']+8 if is_left else p['x']-8
                    y=p['y']+p['h']*((len(phases)-i) if is_left else (i+1))/(len(phases)+1)
                    m.add_line((spines[phase],y),(x,y),dxfattribs={'layer':'PLAN_'+phase,'lineweight':25})
                    m.add_circle((x,y),2,dxfattribs={'layer':'PLAN_'+phase})
                    m.add_circle((spines[phase],y),2,dxfattribs={'layer':'PLAN_'+phase})
                else:
                    x=p['x']+p['w']*(i+1)/(len(phases)+1)
                    y=p['y']+p['h']
                    rail_y=y+25+'RSTN'.index(phase)*14
                    m.add_line((x,rail_y),(x,y+8),dxfattribs={'layer':'PLAN_'+phase,'lineweight':25})
                    m.add_circle((x,y+8),2,dxfattribs={'layer':'PLAN_'+phase})
                fishbone_connections.append(dict(tag=p['tag'],phase=phase,endpoint_status='routing_port_only',terminal_verified=False,connection_role='neutral_pole_requires_verification' if phase=='N' else 'phase'))
        main=next((p for p in placements if p['tag'] in [e['tag'] for e in incoming]),None)
        if main:
            for i,phase in enumerate('RST'):
                port_x=main['x']+main['w']*(i+1)/4
                port_y=main['y']-8
                feed_y=height-305-i*14
                m.add_lwpolyline([(port_x,port_y),(port_x,feed_y),(spines[phase],feed_y)],dxfattribs={'layer':'PLAN_'+phase,'lineweight':35})
                m.add_circle((port_x,port_y),2,dxfattribs={'layer':'PLAN_'+phase})
    # Bounding boxes include each source projection, without resizing.
    for i,a in enumerate(placements):
        for b in placements[i+1:]:
            if a['zone']!=b['zone']:continue
            if min(a['x']+a['w'],b['x']+b['w'])>max(a['x'],b['x']) and min(a['y']+a['h'],b['y']+b['h'])>max(a['y'],b['y']):
                raise ValueError(f"CAD thiết bị chồng nhau: {a['tag']} / {b['tag']}")
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    dxf=out/'TDT_CAD_thiet_bi_nguon.dxf';doc.saveas(dxf)
    if doc.audit().errors:raise ValueError('DXF audit failed')
    backend=svg.SVGBackend()
    frontend=Frontend(RenderContext(doc),backend,config=Configuration(color_policy=ColorPolicy.COLOR if distribution_method=='fabricated_fishbone' else ColorPolicy.BLACK,background_policy=BackgroundPolicy.WHITE))
    if distribution_method=='fabricated_fishbone':
        def display_colors(entity, properties):
            colors={'PLAN_R':'#c62828','PLAN_S':'#c29400','PLAN_T':'#2356c4'}
            properties.color=colors.get(entity.dxf.layer,'#111111')
        frontend.push_property_override_function(display_colors)
    frontend.draw_layout(m)
    picture=backend.get_string(layout.Page(420,297,layout.Units.mm))
    (out/'TDT_CAD_thiet_bi_nguon.svg').write_text(picture,encoding='utf-8')
    rows_html=''.join('<tr>'+''.join(f'<td>{html.escape(str(v))}</td>' for v in [p['tag'],p['original_spec'],p['cad_name'],p['physical_units_per_cad'],f"{p['w']:g} × {p['h']:g}",p['zone'],p['source']])+'</tr>' for p in placements)
    page='''<!doctype html><meta charset="utf-8"><title>TĐT — CAD thiết bị nguồn</title><style>body{font:15px Arial;color:#17334f;background:#eef3f7;margin:24px}main{background:white;padding:25px;max-width:1500px;margin:auto}svg{width:100%;height:auto}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccd7df;padding:8px;text-align:left}.note{background:#fff2d5;padding:15px}button{padding:10px}</style><main><h1>TĐT — bố trí bằng CAD thực tế trong CatalogTB</h1><p>H1000 × W600 × D300 mm theo sơ đồ. CAD chèn nguyên tỷ lệ; PE bố trí phía dưới; N là thanh cái dọc trong cụm R–S–T–N, có nhánh xương cá; MCB xếp dòng định mức từ lớn đến bé, cân bằng bề rộng hai bên, cân bằng các hàng; cần model cho phép lắp sát và kiểm tra hệ số nhiệt. Thiết bị gắn cánh bố trí riêng.</p><p class="note">CAD nguồn là hình tham khảo theo dòng thiết bị, chưa xác nhận mã mua hàng. MCCB dùng hình khung 250AF để xem bố trí; chưa chứng minh đạt 200A/85kA. BKN chưa chốt biến thể 30A. Kích thước mặt CAD không xác nhận chiều sâu, lỗ gá, khoảng cách điện hoặc tư thế lắp. Vùng rail/máng/cầu đấu là đề xuất chưa chốt.</p><button onclick="window.print()">In / lưu PDF</button>'''+picture+'<h2>Đối chiếu từng hình CAD đã chèn</h2><table><tr><th>Ký hiệu</th><th>Yêu cầu sơ đồ</th><th>Hồ sơ CAD nguồn</th><th>Biên hình CAD (mm)</th><th>Vị trí</th><th>Nguồn</th></tr>'+rows_html+'</table><p>PE?, N?, FU? là CAD đề xuất, chưa chốt số cọc, ruột/đế hoặc thông số điện. Giao tiếp cháy và dự phòng chưa chốt mã. Không suy dây hoặc tiết diện đồng từ dòng CB/hình CAD. Chưa có kiểm tra 3D, cáp, nhiệt hoặc phối hợp bảo vệ. Cần người phụ trách kỹ thuật duyệt trước chế tạo.</p></main>'
    (out/'Thu_ve_tu_TDT.html').write_text(page,encoding='utf-8')
    from app.services.ai.distribution_review import review_distribution
    distribution=review_distribution(devices,requested_method=distribution_method)
    distribution['routing_preview']=fishbone_connections
    table=''.join('<tr><td>'+html.escape(a['name'])+'</td><td>'+html.escape(a['topology'])+'</td><td>'+html.escape(', '.join(a['missing_information']))+'</td></tr>' for a in distribution['alternatives'])
    section='<h2>Hệ đi dây / đồng</h2><p>Bản bố trí này chưa vẽ dây lực, thanh lược hoặc đồng xương cá. Chỉ đặt sát CB không chứng minh đã cấp nguồn bằng xương cá. Có thể phối hợp thanh đồng chính với dây nhánh; cần xác nhận điều kiện từng phương án.</p><table><tr><th>Phương án</th><th>Đường cấp nguồn</th><th>Còn thiếu để chọn</th></tr>'+table+'</table>'
    if distribution_method=='fabricated_fishbone':
        section=section.replace('Bản bố trí này chưa vẽ dây lực, thanh lược hoặc đồng xương cá. Chỉ đặt sát CB không chứng minh đã cấp nguồn bằng xương cá. Có thể phối hợp thanh đồng chính với dây nhánh; cần xác nhận điều kiện từng phương án.', 'Đã chọn phương án đồng xương cá theo yêu cầu người dùng và vẽ lớp sơ đồ phân pha R/S/T. Các đường/răng là tuyến chức năng, không phải kích thước đồng hoặc vị trí cọc chế tạo. Điểm cuối dừng ngoài thiết bị, chưa nối vào cọc chưa xác minh. CB 2P giữ pha theo nhãn nguồn; cực còn lại/N cần xác nhận. Cầu chì ở bên phải theo tuyến dây từ cánh tủ bên phải của phương án này. N có xương cá riêng, nhận N nguồn độc lập với MCCB 3P. PE tách riêng. Nhánh N tới CB chỉ là đề xuất cho lộ 2P/4P; cần xác minh cực N và không dùng chung N sau các RCD. Lộ 3P cần cầu đấu N riêng nếu tải dùng N.')
    page=page.replace('<th>Biên hình CAD (mm)</th>','<th>SL thành phần / CAD</th><th>Biên hình CAD (mm)</th>')
    page=page.replace('PE?, N?, FU? là CAD đề xuất, chưa chốt số cọc, ruột/đế hoặc thông số điện.','PE?, N? là đề xuất cần kiểm tra cọc. FU1-FU3 có 3 cầu chì theo xác nhận người dùng: 1 CAD dãy 3 đế, không phải 3 dãy; ruột, mã và định mức chưa chốt.')
    page=page.replace('</main>',section+'</main>')
    page=page.replace('H1000 × W600 × D300 mm theo sơ đồ.',f'H{height:g} × W{width:g} × D{depth:g} mm — bản đề xuất bố trí.')
    if branch_arrangement=='two_rows_two_banks':
        page=page.replace('<button onclick="window.print()">','<p><strong>Hai hàng ngang, mỗi hàng có nhóm trái/phải; xương cá giữa tủ.</strong></p><button onclick="window.print()">')
    if original_dimensions and tuple(map(float,original_dimensions))!=tuple(map(float,dimensions)):
        oh,ow,od=map(float,original_dimensions)
        page=page.replace('<h1>TĐT — bố trí bằng CAD thực tế trong CatalogTB</h1>',f'<h1>TĐT — bố trí hai hàng, hai bên</h1><p class="note">Kích thước sơ đồ H{oh:g} × W{ow:g} × D{od:g} → đề xuất H{height:g} × W{width:g} × D{depth:g} mm. Chưa duyệt đổi vỏ; khoảng bố trí là giả thiết rà soát, cần kiểm tra cọc/cáp/nhiệt.</p>')
    if branch_arrangement=='two_vertical_banks':
        page=page.replace('TĐT — bố trí bằng CAD thực tế trong CatalogTB','TĐT — CB đối hướng, khung theo bố trí mới')
        page=page.replace('bố trí hai hàng, hai bên','hai dãy CB dọc, xương cá giữa tủ')
        page=page.replace('<button onclick=','<p class="note"><strong>Đã đổi sang hai dãy dọc trái/phải như ảnh tham khảo. CB lớn ở trên; CB trái xoay 270°, CB phải xoay 90° theo yêu cầu bố trí đối hướng. MCCB tổng ở trên. Biên CAD CB 3P sau xoay: 82 × 54 mm; 2P: 82 × 36 mm. Chưa xác minh cọc và điều kiện lắp của model.</strong></p><button onclick=')
    (out/'Thu_ve_tu_TDT.html').write_text(page,encoding='utf-8')
    (out/'Phuong_an_phan_phoi_nguon.json').write_text(json.dumps(distribution,ensure_ascii=False,indent=2),encoding='utf-8')
    material_rows=[dict(id='layout-neutral',row_type='item',name='Thanh đồng N gia công',spec=f"Dài theo bố trí {p['length_mm']:g} mm; tiết diện, lỗ đấu và gá đỡ chờ xác minh",unit='Thanh',quantity=1,unit_price=None,line_total=None,price_status='pending',category='N',notes='Bóc theo CAD bố trí; chưa chốt chế tạo',panel_code=panel_code) for p in placements if p.get('status')=='custom_fabricated_review']
    completion_checks = {
        'enclosure_source_verified': False,
        'neutral_bar_placed': any(e['device']['category'] == 'N' for e in extras),
        'protective_earth_bar_placed': any(e['device']['category'] == 'PE' for e in extras),
        'terminals_verified': False,
        'conductor_sections_verified': False,
    }
    branch_boxes=[p for p in placements if p['tag'] in [e['tag'] for e in branches]]
    left=[p for p in branch_boxes if p['x']<offset+width/2];right=[p for p in branch_boxes if p['x']>=offset+width/2]
    spacing_review=dict(user_design_policy=design_policy,main_current_a=main_current,branch_to_busbar_edge_gap_mm=route_gap,closed_door_collision_status='unverified_missing_depth_and_handle_envelopes',opposing_device_gap_mm=min(p['x'] for p in right)-max(p['x']+p['w'] for p in left) if left and right else None,spine_pitch_mm=pitch,clearance_compliance='unverified',required_inputs=rules['required_before_release'],notes=['Kích thước 2D chỉ dùng bố trí; giao tuyến không phải mối nối điện','Răng đồng chéo qua thanh khác cần phân lớp theo chiều sâu và xác minh khoảng cách điện','Khoảng sát CB cần kiểm tra nhiệt và tư thế lắp theo model'])
    neutral_routes=[r for r in fishbone_connections if r['phase']=='N']
    if neutral_routes:
        material_rows.append(dict(id='layout-neutral-teeth',row_type='requirement',name='Nhánh đồng N xương cá',quantity=len(neutral_routes),unit='Nhánh',unit_price=None,line_total=None,price_status='pending',category='N',panel_code=panel_code,notes='Số tuyến đề xuất; chiều dài, tiết diện, gá đỡ và cực N chưa xác minh'))
    gap=spacing_review['opposing_device_gap_mm']
    spacing_section='<h2>Khoảng cách bố trí R–S–T–N</h2><p>Khoảng trống giữa biên hai dãy CB: '+(f'{gap:g} mm' if gap is not None else 'chưa xác định')+f'. Bước tim thanh cái đề xuất: {pitch:g} mm. Đây là khoảng bố trí 2D, không phải kết luận đạt khoảng cách điện.</p><p>N có thanh dọc và răng riêng. Điểm cấp N phải lấy từ N nguồn; không nối N qua MCCB 3P. Phải kiểm tra các thanh giao nhau theo chiều sâu, tiết diện, cọc đấu, cách điện, nhiệt và khả năng chịu ngắn mạch.</p>'
    (out/'Thu_ve_tu_TDT.html').write_text(page.replace('</main>',spacing_section+'</main>'),encoding='utf8')
    result=dict(spacing_review=spacing_review,design_rule_profile='data/design_rules/fishbone_rstn.json',material_rows=material_rows,enclosure_source=enclosure_source,status='reference_layout_needs_review',release_ready=False,
                completion_checks=completion_checks,placements=placements,missing=missing,
                distribution_method=distribution_method,control_wire_entry='RIGHT',
                branch_arrangement=branch_arrangement,original_dimensions=original_dimensions,proposed_dimensions=dimensions,
                dxf=str(dxf),preview=str(out/'Thu_ve_tu_TDT.html'),row_count=2 if branch_arrangement in ('two_rows_two_banks','two_vertical_banks') else len(rows),bank_group_count=len(rows),depth_checked=False)
    (out/'CAD_layout_review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result

"""Export an editable reference even when some device geometry is unresolved."""
from pathlib import Path
from uuid import uuid4
import math
import ezdxf


class ReferenceLayoutGenerator:
    @staticmethod
    def generate(project_id, output_dir, dimensions, devices, kind='indoor', product_name=''):
        reference_dimensions = dimensions
        dimension_basis = 'source_reference'
        if not dimensions:
            # Missing source dimensions must not prevent a review drawing when
            # actual device envelopes provide a basis for a proposed enclosure.
            from .device_envelope import selected_envelope
            known = []
            for row in devices:
                try:
                    envelope = selected_envelope(row)
                    if all(math.isfinite(v) and v > 0 for v in envelope):
                        known.append(row)
                except (ValueError, TypeError, KeyError, OSError):
                    continue
            if not known:
                raise ValueError('Chưa có bao hình CAD thiết bị để đề xuất kích thước tủ nháp.')
            from .enclosure_cad_generator import EnclosureCadGeneratorService
            proposal = EnclosureCadGeneratorService.calculate_enclosure_specs(known)
            dimensions = tuple(proposal[axis] for axis in ('height', 'width', 'depth'))
            dimension_basis = 'proposed_from_available_device_geometry'
        if len(dimensions) != 3 or any(
                not math.isfinite(float(v)) or float(v) <= 0 for v in dimensions):
            raise ValueError('Kích thước tham khảo phải có đủ H×W×D lớn hơn 0.')
        from .source_project_generator import SourceProjectGenerator
        try:
            result = SourceProjectGenerator.generate(project_id, output_dir, dimensions,
                devices=devices, allow_partial=True, kind=kind, product_name=product_name)
            doc = ezdxf.readfile(result['path'])
        except (ValueError, OSError) as exc:
            # These are dimensioned exterior views, not invented device bodies
            # or fabrication details of an unavailable source cabinet.
            h, w, d = map(float, dimensions)
            doc = ezdxf.new('R2010'); doc.units = 4
            m = doc.modelspace()
            for label, x, width in [('MAT TRUOC', 0, w), ('MAT BEN', w+100, d)]:
                m.add_lwpolyline([(x,0),(x+width,0),(x+width,h),(x,h)],close=True)
                m.add_text(f'{label}: {width:g} x {h:g} mm',dxfattribs={'height':10,'insert':(x,h+20)})
                m.add_linear_dim(base=(x,-30),p1=(x,0),p2=(x+width,0),angle=0).render()
                m.add_linear_dim(base=(x-30,0),p1=(x,0),p2=(x,h),angle=90).render()
            interior_x = w+d+220
            m.add_lwpolyline([(interior_x,0),(interior_x+w,0),(interior_x+w,h),(interior_x,h)],close=True)
            m.add_text('BO TRI DU KIEN - CHUA DUYET GIA CONG',dxfattribs={'height':10,'insert':(interior_x,h+20)})
            from .library_assets import insert_library_asset
            from .catalogtb_assets import resolve, instance_count
            from .device_envelope import selected_envelope
            placements, missing = [], []
            from .reserved_space import allocate, draw
            available_region, reservation = allocate((interior_x+40,40,interior_x+w-40,h-40))
            draw(m, reservation)
            cursors = {'outer_door':[40,h-40,0], 'mounting_plate':[40,h-40,0]}
            for row in devices:
                tag = row.get('tag') or row.get('name')
                try:
                    asset_id = (row.get('cad') or {}).get('asset_id')
                    if not asset_id: raise ValueError('Chưa chọn bao hình')
                    ew, eh, ed = selected_envelope(row)
                    if ed > d-40 or ew > w-80: raise ValueError('Không đủ không gian')
                    asset = resolve(asset_id, 'front')
                    face = row.get('mounting_face') or row.get('owner_face')
                    if not face:
                        face = 'outer_door' if asset['category'] in ('LIGHT','METER','SELECTOR') else 'mounting_plate'
                    if face not in cursors: raise ValueError('Mặt lắp chưa hỗ trợ')
                    count = instance_count(row.get('quantity') or 1, asset)
                    state = list(cursors[face]); planned=[]
                    for _ in range(count):
                        xx, yy, row_height = state
                        if xx+ew > w-40: xx, yy, row_height = 40, yy-row_height-40, 0
                        lower_limit = available_region[1] if face=='mounting_plate' else 40
                        if yy-eh < lower_limit: raise ValueError('Không đủ chiều cao ngoài vùng dự phòng')
                        planned.append((xx,yy-eh))
                        state = [xx+ew+20, yy, max(row_height,eh)]
                    for xx, yy in planned:
                        px = xx+(interior_x if face=='mounting_plate' else 0)
                        insert_library_asset(m,asset_id,px,yy)
                        m.add_text(str(tag),dxfattribs={'height':8,'insert':(px,yy-12)})
                        placements.append({'tag':tag,'asset_id':asset_id,'face':face,
                            'x':px,'y':yy,'w':ew,'h':eh,'depth':ed,'status':'proposed_reference'})
                    cursors[face]=state
                except (ValueError,TypeError,KeyError,OSError):
                    missing.append(tag)
            folder = Path(output_dir)/str(project_id)/'cad'/'cabinet_forms'
            folder.mkdir(parents=True,exist_ok=True)
            result = {'path':str(folder/f'CAD_NHAP_{uuid4().hex[:10]}.dxf'),
                'template_id':None,'source':'Kích thước vỏ tủ trong hồ sơ nguồn',
                'dimensions':dict(zip(('height','width','depth'),(h,w,d))),
                'minimum_required':dict(zip(('height','width','depth'),(h,w,d))),
                'placements':placements, 'unmatched_devices':missing,
                'form_review_reason':str(exc)}
        from ezdxf import bbox
        bounds = bbox.extents(doc.modelspace(),fast=True)
        x = bounds.extmax.x+80 if bounds.has_data else 0
        y = bounds.extmax.y if bounds.has_data else float(dimensions[0])
        m = doc.modelspace()
        if 'REFERENCE_REVIEW' not in doc.layers:
            doc.layers.new('REFERENCE_REVIEW',dxfattribs={'color':1})
        def note(text, yy):
            m.add_text(text,dxfattribs={'height':10,'insert':(x,yy),'layer':'REFERENCE_REVIEW'})
        note('CAD NHAP - CHUA DUYET SAN XUAT / DON GIA',y)
        note('THIET BI CHUA BO TRI - KHONG SUY DIEN KICH THUOC',y-22)
        note('KHOANG CHUA ME / DAY: DE XUAT, CAN XAC NHAN TRUOC GIA CONG', y+22)
        if result.get('dimension_changes'):
            note('KICH THUOC NGUON THAM KHAO - FORM DE XUAT: '+str(tuple(dimensions)),y+44)
        if dimension_basis == 'proposed_from_available_device_geometry':
            note('KICH THUOC TU DE XUAT TU BAO HINH HIEN CO - CAN RA SOAT',y+66)
        missing = set(result['unmatched_devices'])
        for index,row in enumerate(r for r in devices if (r.get('tag') or r.get('name')) in missing):
            note(f"{row.get('tag') or ''} | {row.get('name') or ''} | {row.get('spec') or 'Chua ro thong so'} | SL {row.get('quantity') or 1}",y-44-index*20)
        target = Path(result['path'])
        if not target.name.startswith('CAD_NHAP_'):
            target = target.with_name('CAD_NHAP_' + target.name)
        result['path'] = str(target)
        from .reserved_space import from_dxf
        result['reserve_space'] = from_dxf(doc, result.get('placements') or [])
        doc.saveas(target)
        result.update(status='reference_layout_needs_review',release_ready=False,
                      incomplete=True,form_review_reason=result.get('form_review_reason'),
                      dimension_basis=dimension_basis,source_reference_dimensions=reference_dimensions)
        return result

"""Select and save a complete, traceable cabinet form from the CAD library."""
from __future__ import annotations

from pathlib import Path
import io
import copy
import unicodedata
from uuid import uuid4

import ezdxf
from ezdxf import bbox

from app.services.cad import cabinet_templates
from app.services.cad.placement_clearances import usable_region, reference_region, device_gap


class SourceProjectGenerator:
    @staticmethod
    def _layout_form(source_item, dimensions):
        """Move verified face regions through the same source DIM stretch bands."""
        item = copy.deepcopy(source_item)
        nominal = item.get('dimensions') or dimensions
        delta = {axis:dimensions[axis]-nominal[axis] for axis in dimensions}
        if any(abs(value) > .01 for value in delta.values()):
            source = ezdxf.readfile(cabinet_templates.source_path(source_item))
            axes = cabinet_templates.stretch_axes(source, nominal)
            for face in item.get('faces', []):
                if face.get('clean_bounds'):
                    a,b,c,d = face['clean_bounds']
                    face['clean_bounds'] = [cabinet_templates.map_coordinate(a,axes[0],delta),
                        cabinet_templates.map_coordinate(b,axes[1],delta),
                        cabinet_templates.map_coordinate(c,axes[0],delta),
                        cabinet_templates.map_coordinate(d,axes[1],delta)]
        return item

    @staticmethod
    def _interior_region(doc, dimensions, source_item=None, allow_reference=False):
        """Find the source's dimensioned interior elevation, not a guessed sheet cell."""
        faces = [f for f in (source_item or {}).get('faces',[]) if f.get('kind') == 'mounting_plate' and f.get('clean_bounds')]
        if len(faces) == 1:
            left,bottom,right,top = faces[0]['clean_bounds']
            # A real mounting plate can be smaller than the exterior cabinet.
            if 0 < right-left <= dimensions['width']+1 and 0 < top-bottom <= dimensions['height']+1:
                region_fn = reference_region if allow_reference else usable_region
                return region_fn((left,bottom,right,top),source_item,'mounting_plate')
        def plain(value):
            value = ''.join(c for c in unicodedata.normalize('NFD', value.upper()) if not unicodedata.combining(c))
            return value.replace('Đ', 'D')

        labels = [e for e in doc.modelspace().query('TEXT MTEXT')
                  if 'MAT TRONG TU' in plain(e.dxf.text if e.dxftype() == 'TEXT' else e.text)]
        if not labels:
            raise ValueError('Form nguồn chưa xác định được mặt trong tủ để bố trí thiết bị.')
        label_x = labels[0].dxf.insert.x
        widths = []
        heights = []
        for dim in doc.modelspace().query('DIMENSION'):
            p, q = dim.dxf.get('defpoint2'), dim.dxf.get('defpoint3')
            if p is None or q is None:
                continue
            dx, dy = abs(p.x - q.x), abs(p.y - q.y)
            if abs(dx - dimensions['width']) < 2 and dy < 2:
                widths.append((min(p.x, q.x), max(p.x, q.x), min(p.y, q.y)))
            if dy >= dimensions['height'] - 150 and dx < 2:
                heights.append((min(p.y, q.y), max(p.y, q.y), p.x))
        if not widths or not heights:
            raise ValueError('Form nguồn thiếu đường kích thước xác nhận vùng lắp đặt.')
        left, right, _ = min(widths, key=lambda row: abs((row[0] + row[1]) / 2 - label_x))
        bottom, top, _ = min(heights, key=lambda row: abs(row[2] - right))
        region_fn = reference_region if allow_reference else usable_region
        return region_fn((left,bottom,right,top),source_item,'mounting_plate')

    @staticmethod
    def _place_devices(dxf, devices, dimensions, source_item, allow_partial=False):
        from app.services.cad.library_assets import requested_asset, insert_library_asset
        doc = ezdxf.read(io.StringIO(dxf))
        left, bottom, right, top = SourceProjectGenerator._interior_region(doc, dimensions, source_item, allow_reference=allow_partial)
        def gap_for(device, axis):
            try:
                return device_gap(device, axis)
            except ValueError:
                if not allow_partial: raise
                return 40 if axis=='vertical' else 20
        entries = []
        missing = []
        for device in devices:
            linked, asset_id = requested_asset(device)
            if not linked or not asset_id:
                missing.append(device.get('tag') or device.get('name') or '?')
                continue
            from app.services.cad.physical_layout_engine import PhysicalLayoutEngine, MountingType
            depth = (device.get('dimensions') or {}).get('d')
            if depth and float(depth) > dimensions['depth']:
                raise ValueError('Chiều sâu thiết bị vượt chiều sâu form: '+str(device.get('tag') or device.get('name')))
            mounting = PhysicalLayoutEngine.classify_mounting(device)
            face = device.get('mounting_face') or device.get('owner_face')
            if not face and mounting in (MountingType.DOOR_MOUNTED, MountingType.INNER_COVER_MOUNTED):
                if allow_partial:
                    missing.append(device.get('tag') or device.get('name') or '?')
                    continue
                raise ValueError('Cần vùng cánh tủ được xác nhận; không đặt thiết bị gắn cánh lên mặt trong.')
            face = face or 'mounting_plate'
            if face not in ('mounting_plate','inner_door','outer_door'):
                raise ValueError('Mặt lắp thiết bị chưa được ánh xạ với form nguồn: '+str(face))
            if str(asset_id).startswith('tb:'):
                from app.services.cad.catalogtb_assets import resolve
                source = ezdxf.readfile(resolve(asset_id)['path'])
            else:
                from app.api.v1.endpoints.cad_library import download_layout
                source = ezdxf.readfile(download_layout(asset_id).path)
            bounds = bbox.extents(source.modelspace())
            if not bounds.has_data:
                missing.append(device.get('tag') or device.get('name') or '?')
                continue
            qty = max(1, min(int(device.get('quantity') or 1), 100))
            width,height = bounds.size.x,bounds.size.y
            if str(asset_id).startswith('tb:'):
                from app.services.cad.catalogtb_assets import resolve, instance_count
                from app.services.cad.device_envelope import _bounds
                asset=resolve(asset_id)
                qty = instance_count(qty, asset)
                width,height = _bounds(asset)
            for _ in range(qty):
                entries.append((device, asset_id, width, height, face))
        # Incoming protection first; then outgoing protection, then controls.
        def rank(entry):
            device = entry[0]
            section = str(device.get('section') or '').upper()
            cat = str(device.get('category') or '').upper()
            incoming = section in ('INCOMER', 'ĐẦU VÀO', 'DAU VAO', 'NGUỒN CẤP') or 'TỔNG' in str(device.get('name') or '').upper()
            return (0 if incoming else 1 if cat in ('ACB', 'MCCB', 'MCB', 'RCBO', 'RCCB') else 2,
                    -float(device.get('in_a') or 0), str(device.get('tag') or ''))
        entries.sort(key=rank)
        regions={'mounting_plate':(left,bottom,right,top)}
        for face in ('inner_door','outer_door'):
            matches=[f for f in source_item.get('faces',[]) if f.get('kind')==face and f.get('clean_bounds')]
            if len(matches)==1:
                b=matches[0]['clean_bounds']
                regions[face]=(reference_region if allow_partial else usable_region)(b,source_item,face)
        states={face:[b[0],b[3],0.0] for face,b in regions.items()}
        placements = []
        for device, asset_id, width, height, face in entries:
            if face not in regions:
                raise ValueError('Form nguồn thiếu vùng xác nhận cho mặt '+face)
            left,bottom,right,top=regions[face]
            x,row_top,row_height=states[face]
            if width <= 0 or height <= 0 or width > right-left or height > top-bottom:
                raise ValueError(f"Khối CAD {asset_id} không vừa vùng lắp đặt của form nguồn.")
            if x + width > right:
                x, row_top, row_height = left, row_top - row_height - gap_for(device,'vertical'), 0.0
            if row_top - height < bottom:
                raise ValueError('Các thiết bị CAD nguồn không đủ chỗ trên mặt trong tủ; cần form lớn hơn.')
            y = row_top - height
            insert_library_asset(doc.modelspace(), asset_id, x, y)
            placements.append({'tag': device.get('tag'), 'asset_id': asset_id, 'x': x, 'y': y,
                               'mounting_face':face,'width':width,'height':height,
                               'electrical_spec_verified':False})
            gap=gap_for(device,'horizontal')
            x += width + gap
            row_height = max(row_height, height)
            states[face]=[x,row_top,row_height]
        doc.update_extents()
        stream = io.StringIO()
        doc.write(stream)
        return stream.getvalue(), placements, missing

    @staticmethod
    def generate(project_id: int, output_dir: str, dimensions, kind: str = "indoor", product_name: str = "", devices=None, allow_partial=False) -> dict:
        if not dimensions or len(dimensions) != 3:
            raise ValueError("Chưa có kích thước tủ H×W×D được xác định từ bản vẽ hoặc người dùng.")
        height, width, depth = (float(value) for value in dimensions)
        requested = {"height": height, "width": width, "depth": depth}
        if any(value <= 0 for value in requested.values()):
            raise ValueError("Kích thước tủ phải lớn hơn 0.")
        if height >= 1800 and width < height / 3:
            raise ValueError("Tủ đứng quá hẹp so với chiều cao; cần kiểm tra lại kích thước và bố trí thiết bị.")
        matches = cabinet_templates.candidates(requested, kind=kind)
        # A real, slightly larger source cabinet is safer than stretching an
        # unrelated sheet to an exact but unverified calculated envelope.
        fitting = [item for item in matches if item.get("status") in ("source", "needs_review")
                   and item.get("dimensions")
                   and all(requested[axis] <= item["dimensions"][axis] for axis in requested)]
        fitting.sort(key=lambda item: (
            item["dimensions"]["height"] * item["dimensions"]["width"] * item["dimensions"]["depth"],
            item["distance"], item["id"],
        ))
        eligible = [item for item in matches if item in fitting or item['can_generate']]
        eligible.sort(key=lambda item: (
            (item['dimensions']['height']*item['dimensions']['width']*item['dimensions']['depth'])
                if item in fitting else height*width*depth, item['distance'], item['id']))
        match = None
        attempted_forms = []
        prepared = None
        for candidate in eligible:
            try:
                candidate_dimensions = candidate['dimensions'] if candidate in fitting else requested
                candidate_dxf = cabinet_templates.generate(candidate['id'], candidate_dimensions, product_name=product_name)
                candidate_placements, candidate_missing = [], []
                if devices:
                    layout_form = SourceProjectGenerator._layout_form(candidate, candidate_dimensions)
                    candidate_dxf, candidate_placements, candidate_missing = SourceProjectGenerator._place_devices(
                        candidate_dxf, devices, candidate_dimensions, layout_form, allow_partial=allow_partial)
                    if candidate_missing and not allow_partial:
                        raise ValueError('Thiếu CAD thiết bị: ' + ', '.join(candidate_missing))
            except ValueError as exc:
                attempted_forms.append({'template_id': candidate['id'], 'reason': str(exc)})
                continue
            match = candidate
            prepared = (candidate_dxf, candidate_placements, candidate_missing)
            break
        if not match:
            detail = '; '.join(attempt['template_id'] + ': ' + attempt['reason'] for attempt in attempted_forms[:5])
            raise ValueError("Chưa có form nguồn phù hợp sau kiểm tra bố trí thực tế." + (' ' + detail if detail else ''))
        selected = match["dimensions"] if match in fitting else requested
        dxf, placements, missing = prepared
        folder = Path(output_dir) / str(project_id) / "cad" / "cabinet_forms"
        folder.mkdir(parents=True, exist_ok=True)
        filename = f"FormTu_{match['id']}_H{selected['height']:g}W{selected['width']:g}D{selected['depth']:g}_{uuid4().hex[:10]}.dxf"
        path = folder / filename
        path.write_text(dxf, encoding="utf-8")
        return {"path": str(path), "template_id": match["id"], "source": match["filename"],
                "dimensions": selected, "minimum_required": requested,
                "placements": placements, "unmatched_devices": missing,
                "clearance_status": 'proposed_requires_review' if allow_partial else 'source_verified',
                "dimension_changes": {axis:{'requested':requested[axis],'selected':selected[axis]}
                    for axis in requested if abs(requested[axis]-selected[axis])>.01},
                "form_fit_attempts": attempted_forms,
                "status": "reference_layout_needs_review",
                "release_ready": False}

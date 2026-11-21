"""Derive equipment selection proposals from each panel's metering context."""
import re
import unicodedata
from copy import deepcopy


def _text(value):
    return ''.join(c for c in unicodedata.normalize('NFD', str(value or '').lower().replace('đ', 'd'))
                   if not unicodedata.combining(c))


def metering_kind(row):
    category = str(row.get('category') or '').upper()
    if category in {'CT', 'AMMETER', 'VOLTMETER', 'ENERGY_METER', 'LIGHT', 'PILOT_LIGHT'}:
        return 'LIGHT' if category == 'PILOT_LIGHT' else category
    name = _text(row.get('name'))
    if category not in {'', 'METER', 'MEASURING'} or 'chuyen mach' in name:
        return category
    for pattern, kind in [(r'bien dong', 'CT'), (r'ampe|ammeter', 'AMMETER'),
                          (r'von ke|volt|dong ho.*dien ap', 'VOLTMETER'),
                          (r'cong to', 'ENERGY_METER'), (r'den bao pha', 'LIGHT')]:
        if re.search(pattern, name):
            return kind
    return category


def ct_ratios(value, *, unit_optional=False):
    unit = r'(?:\s*A\b)?' if unit_optional else r'\s*A\b'
    return {(float(p.replace(',', '.')), float(s.replace(',', '.')))
            for p, s in re.findall(r'(?<![\d./])(\d+(?:[.,]\d+)?)\s*A?\s*/\s*(\d+(?:[.,]\d+)?)(?![\d.,/])' + unit,
                                  str(value or ''), re.I)
            if float(p.replace(',', '.')) > 0 and float(s.replace(',', '.')) > 0}


def display_limits(value, unit):
    return {float(n.replace(',', '.')) for n in re.findall(
        rf'(?<![\d.])0\s*[-–—…~]\s*(\d+(?:[.,]\d+)?)\s*{unit}(?:\s*(?:AC|DC))?\b',
        str(value or ''), re.I)}


def _ratios(rows):
    return {ratio for row in rows if metering_kind(row) == 'CT'
            for ratio in ct_ratios(row.get('spec'), unit_optional=True)}


def enrich_metering_selection(devices):
    """Preserve observed specs/counts and attach an explicit, repeatable proposal."""
    rows = deepcopy(devices)
    members = []
    for row in rows:
        members.append(row)
        for accessory in row.get('accompanying_accessories') or []:
            if isinstance(accessory, dict):
                members.append({**{key: row.get(key) for key in ('panel_code', 'source_filename', 'source_page')},
                                **accessory, '_target': accessory})
    for row in members:
        kind = metering_kind(row)
        # Người dùng yêu cầu: Không phân tích rườm rà cho đèn báo pha (LIGHT), chỉ ghi mỗi tên loại đèn báo pha
        if kind not in {'AMMETER', 'VOLTMETER', 'ENERGY_METER'}:
            continue
        panel = row.get('panel_code')
        related = [item for item in members if panel and item.get('panel_code') == panel
                   and all(not row.get(key) or not item.get(key) or row[key] == item[key]
                           for key in ('source_filename', 'source_page'))]
        # Prefer an explicitly linked CT when multiple circuits share a cabinet.
        linked = [item for item in related if metering_kind(item) == 'CT' and item.get('tag')
                  and (row.get('upstream_device') == item.get('tag') or (row.get('tag') and item.get('downstream_device') == row.get('tag')))]
        explicit_ratios = ct_ratios(row.get('spec')) if kind == 'AMMETER' else set()
        linked_ratios = _ratios(linked)
        ratios = explicit_ratios or linked_ratios or (_ratios(related) if not linked else set())
        ratio = next(iter(ratios)) if len(ratios) == 1 else None
        proposal = dict(basis='engineering_inference', status='proposed', meter_kind=kind,
                        source_spec=row.get('spec') or '', assumptions=[], checks=[])
        if ratio and not linked and not explicit_ratios:
            proposal['status'] = 'conditional'
        if kind == 'AMMETER':
            scales = display_limits(row.get('spec'), 'A')
            if ratio and ((scales and scales != {ratio[0]})
                          or (explicit_ratios and linked_ratios and linked_ratios != explicit_ratios)):
                ratio = None
                proposal.update(status='needs_context', proposed_spec='Cần đối chiếu thang ampe kế với tỷ số TI',
                                reasoning='Thang ghi trên ampe kế và tỷ số TI đang khác nhau. Xác nhận dây nối và thang đo trước khi chọn mã.')
            if ratio:
                primary, secondary = ratio
                proposal.update(proposed_spec=f'Ampe kế AC qua TI, ngõ vào {secondary:g}A, hiển thị 0–{primary:g}A; tỷ số {primary:g}/{secondary:g}A',
                    reasoning=f'Tỷ số TI {primary:g}/{secondary:g} A tương ứng {secondary:g} A ở ngõ vào và {primary:g} A toàn thang. Đồng hồ kim cần đúng mặt thang, đồng hồ số cần cài đúng tỷ số.',
                    input_current_a=secondary, display_range_a=[0, primary], ct_ratio=f'{primary:g}/{secondary:g}')
                proposal['assumptions'].append('Ampe kế nối với TI này; nếu có nhiều mạch đo phải đối chiếu dây nối.')
                proposal['checks'].append('Đồng hồ kim phải đúng mặt thang TI; đồng hồ số phải hỗ trợ cài tỷ số này. Kiểm tra tải VA, cấp chính xác và layout.')
            elif 'proposed_spec' not in proposal:
                proposal.update(status='needs_context', proposed_spec='Ampe kế qua TI; chọn ngõ vào và thang hiển thị theo TI của đúng mạch',
                    reasoning='Có nhiều tỷ số TI khác nhau trong tủ.' if len(ratios) > 1 else 'Chưa xác định được tỷ số TI thuộc đúng mạch đo; không lấy tỷ số từ tủ khác.')
        elif kind == 'VOLTMETER':
            explicit = re.search(r'(?<!\d)(?:0\s*[-–/]\s*)?(\d+(?:\.\d+)?)\s*V(?:AC|DC)?\b', str(row.get('spec') or ''), re.I)
            if explicit:
                proposal.update(proposed_spec=f'Vôn kế theo thông số nguồn: {row.get("spec")}',
                    reasoning='Ưu tiên thông số điện áp đã ghi; chọn cách đấu và tỷ số biến điện áp tương thích, không thay bằng thang mặc định.')
                limits = display_limits(row.get('spec'), 'V')
                if len(limits) == 1:
                    proposal['display_range_v'] = [0, next(iter(limits))]
            else:
                proposal.update(status='needs_context',
                    reasoning='Chưa rõ điện áp cần đo, kiểu đấu trực tiếp hay qua TU và thang vôn kế.')
            proposal['checks'].append('Đối chiếu nguồn, kiểu đấu dây, chuyển mạch V và kích thước cửa tủ trước khi chọn mã.')
        else:
            if ratio:
                primary, secondary = ratio
                proposal.update(proposed_spec=f'Công tơ điện 3 pha gián tiếp qua TI {primary:g}/{secondary:g}A, ngõ vào dòng {secondary:g}A; cài tỷ số {primary:g}/{secondary:g}',
                    reasoning='Mạch công tơ cùng cụm có TI nên đề xuất loại đo gián tiếp tương thích dòng thứ cấp, thay vì công tơ trực tiếp mang dòng sơ cấp.')
            else:
                proposal.update(status='needs_context', proposed_spec='Công tơ điện: xác định trực tiếp/qua TI từ đường nối trước khi chốt ngõ vào',
                    reasoning='Chưa xác định duy nhất TI thuộc mạch công tơ; không gán thông số từ tủ bên cạnh.')
            proposal['assumptions'].append('Xác nhận công tơ nối vào TI cùng cụm; đối chiếu hệ 3 pha 3 dây/4 dây và nguồn điện áp.')
            proposal['checks'].append('Chốt cấp chính xác, đo một/hai chiều, biểu giá và truyền thông theo yêu cầu sử dụng.')
        row.get('_target', row)['selection_analysis'] = proposal
    return rows

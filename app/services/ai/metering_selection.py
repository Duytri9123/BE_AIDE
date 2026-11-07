"""Derive equipment selection proposals from each panel's metering context."""
import re
import unicodedata
from copy import deepcopy


def _text(value):
    return ''.join(c for c in unicodedata.normalize('NFD', str(value or '').lower().replace('đ', 'd'))
                   if not unicodedata.combining(c))


def _kind(row):
    category = str(row.get('category') or '').upper()
    if category in {'CT', 'AMMETER', 'VOLTMETER', 'ENERGY_METER', 'LIGHT', 'PILOT_LIGHT'}:
        return 'LIGHT' if category == 'PILOT_LIGHT' else category
    name = _text(row.get('name'))
    for term, kind in [('bien dong', 'CT'), ('ampe', 'AMMETER'), ('von ke', 'VOLTMETER'),
                       ('cong to', 'ENERGY_METER'), ('den bao pha', 'LIGHT')]:
        if term in name:
            return kind
    return category


def _ratios(rows):
    values = set()
    for row in rows:
        if _kind(row) != 'CT':
            continue
        for primary, secondary in re.findall(r'(?<![\d.])(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*A\b', str(row.get('spec') or ''), re.I):
            if float(primary) > 0 and float(secondary) > 0:
                values.add((float(primary), float(secondary)))
    return values


def enrich_metering_selection(devices):
    """Preserve observed specs/counts and attach an explicit, repeatable proposal."""
    rows = deepcopy(devices)
    members = []
    for row in rows:
        members.append(row)
        for accessory in row.get('accompanying_accessories') or []:
            if isinstance(accessory, dict):
                members.append({**accessory, 'panel_code': row.get('panel_code'), '_target': accessory})
    for row in members:
        kind = _kind(row)
        if kind not in {'AMMETER', 'VOLTMETER', 'ENERGY_METER', 'LIGHT'}:
            continue
        panel = row.get('panel_code')
        related = [item for item in members if panel and item.get('panel_code') == panel]
        # Prefer an explicitly linked CT when multiple circuits share a cabinet.
        linked = [item for item in related if _kind(item) == 'CT' and item.get('tag')
                  and (row.get('upstream_device') == item.get('tag') or (row.get('tag') and item.get('downstream_device') == row.get('tag')))]
        ratios = _ratios(linked or related)
        ratio = next(iter(ratios)) if len(ratios) == 1 else None
        proposal = dict(basis='engineering_inference', status='proposed',
                        source_spec=row.get('spec') or '', assumptions=[], checks=[])
        if ratio and not linked:
            proposal['status'] = 'conditional'
        if kind == 'AMMETER':
            if ratio:
                primary, secondary = ratio
                proposal.update(proposed_spec=f'Ampe kế AC qua TI, ngõ vào {secondary:g}A, hiển thị 0–{primary:g}A; tỷ số {primary:g}/{secondary:g}A',
                    reasoning=f'TI cùng mạch/tủ ghi {primary:g}/{secondary:g}A: {secondary:g}A thứ cấp tương ứng {primary:g}A sơ cấp. Ampe kế phải có thang hoặc cài đặt đúng tỷ số TI, không đấu trực tiếp dòng sơ cấp.',
                    input_current_a=secondary, display_range_a=[0, primary], ct_ratio=f'{primary:g}/{secondary:g}')
                proposal['assumptions'].append('Ampe kế nối với TI này; nếu có nhiều mạch đo phải đối chiếu dây nối.')
                proposal['checks'].append('Đồng hồ kim phải đúng mặt thang TI; đồng hồ số phải hỗ trợ cài tỷ số này. Kiểm tra tải VA, cấp chính xác và layout.')
            else:
                proposal.update(status='needs_context', proposed_spec='Ampe kế qua TI; chọn ngõ vào và thang hiển thị theo TI của đúng mạch',
                    reasoning='Có nhiều tỷ số TI khác nhau trong tủ.' if len(ratios) > 1 else 'Chưa xác định được tỷ số TI thuộc đúng mạch đo; không lấy tỷ số từ tủ khác.')
        elif kind == 'LIGHT':
            voltage = re.search(r'(?<!\d)(24|48|110|220|230|380|400)\s*V(?:AC|DC)?\b', str(row.get('spec') or ''), re.I)
            if voltage:
                proposal.update(proposed_spec=f'Đèn báo pha LED {voltage[0].strip()}, màu theo ký hiệu nguồn; kiểu gắn cửa Ø22 mm đề xuất',
                    reasoning=f'Giữ điện áp {voltage[1]}V đã ghi; LED và Ø22 mm là lựa chọn thông dụng để triển khai, chưa phải kích thước đọc từ sơ đồ.')
            else:
                proposal.update(status='conditional', proposed_spec='Đèn báo pha LED 220–230VAC, gắn cửa Ø22 mm, màu theo ký hiệu B/Y/R — đề xuất khi đấu pha–N',
                    reasoning='Chọn loại đèn báo pha phổ biến cho mạch pha–trung tính; không lấy dòng bảo vệ 2A làm thông số đèn.')
                proposal['assumptions'].append('Nguồn pha–N 220–230VAC; nếu đấu pha–pha phải chọn đúng điện áp 380–400VAC, nếu dùng nguồn điều khiển phải theo nguồn đó.')
            proposal['checks'].append('Đối chiếu điện áp, AC/DC, đường kính lỗ trên layout và màu ký hiệu; không tự tăng số lượng lên 3.')
        elif kind == 'VOLTMETER':
            explicit = re.search(r'(?<!\d)(?:0\s*[-–/]\s*)?(\d+(?:\.\d+)?)\s*V(?:AC|DC)?\b', str(row.get('spec') or ''), re.I)
            if explicit:
                proposal.update(proposed_spec=f'Vôn kế theo thông số nguồn: {row.get("spec")}',
                    reasoning='Ưu tiên thông số điện áp đã ghi; chọn cách đấu và tỷ số biến điện áp tương thích, không thay bằng thang mặc định.')
            else:
                proposal.update(status='conditional', proposed_spec='Vôn kế AC 0–500V, đo trực tiếp; mặt 72×72 mm đề xuất theo layout',
                    reasoning='Thang 0–500V bao phủ điện áp dây của hệ hạ áp 380/220V hoặc 400/230V thường dùng.')
            proposal['assumptions'].append('Hệ hạ áp 380–400V và đo trực tiếp; nếu có biến điện áp VT/PT phải chọn ngõ vào và thang theo tỷ số VT/PT.')
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

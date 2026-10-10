"""File creation and engineering completion are separate outcomes."""


def output_status(cad_file, quotation_file, layout, conflicts=None, *, reason=None, devices=None):
    layout = layout or {}
    blockers = []
    reconciliation=layout.get('source_reconciliation')
    if cad_file and not reconciliation:
        blockers.append('Chưa có kết quả đối chiếu nguồn theo từng thiết bị để xác nhận CAD hoàn tất.')
    if reconciliation and not reconciliation.get('release_ready'):
        blockers.append('Chưa giải quyết đối chiếu sơ đồ, báo giá và CAD: '+', '.join(reconciliation.get('unresolved_items') or reconciliation.get('unanalysed') or ['thiếu bằng chứng']))
    if not cad_file:
        blockers.append('Chưa lưu được file CAD thiết kế.')
        if reason:
            blockers.append(str(reason))
        unselected=[d.get('tag') or d.get('name') for d in (devices or []) if not (d.get('cad') or {}).get('asset_id')]
        if unselected:
            blockers.append('Cần ghép CAD cho thiết bị: '+', '.join(str(tag) for tag in unselected)+'.')
    if layout.get('status') == 'reference_layout_needs_review':
        blockers.append('CAD nguồn đã bố trí; cần xác minh model, chiều sâu, đầu nối và điều kiện lắp đặt.')
    if cad_file and not layout.get('placements'):
        blockers.append('Chưa xác nhận bố trí thiết bị trong CAD.')
    if layout.get('release_ready') is False and layout.get('status') != 'reference_layout_needs_review':
        blockers.append('Thiết kế chưa được xác nhận đủ điều kiện xuất bản.')
    placed_tags = {p.get('tag') for p in layout.get('placements', [])}
    if cad_file and any(d.get('tag') and d['tag'] not in placed_tags for d in (devices or [])):
        blockers.append('Chưa đối chiếu đủ thiết bị đầu vào với CAD đã bố trí.')
    if layout.get('missing') or layout.get('unmatched_devices'):
        blockers.append('Còn thiết bị chưa được bố trí bằng CAD.')
    if conflicts:
        blockers.append('Còn xung đột bố trí cần xử lý.')
    ready = not blockers
    return dict(success=ready, status='complete' if ready else 'needs_review',
                cad_status='ready' if ready else 'needs_review', cad_blockers=blockers)

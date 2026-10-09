"""Measure body edges; never turn a 2D measurement into electrical approval."""
def measure(placements, devices, width, height, offset, policy, spines=None, half_bar_width=5):
    by_tag = {d.get('tag'): d for d in devices}
    inside = [p for p in placements if p['zone'] == 'interior']
    margins = []
    for p in inside:
        margins.append(dict(tag=p['tag'], left_mm=p['x']-offset,
                            right_mm=offset+width-p['x']-p['w'],
                            bottom_mm=p['y'], top_mm=height-p['y']-p['h']))
    main = [p for p in inside if by_tag.get(p['tag'],{}).get('category') in ('MCCB','ACB')]
    branches = [p for p in inside if by_tag.get(p['tag'],{}).get('category') in ('MCB','RCBO','RCCB')]
    main_gap = min((p['y'] for p in main),default=height)-max((p['y']+p['h'] for p in branches),default=height) if main and branches else None
    bar_gaps = []
    if spines:
        bar_left, bar_right = min(spines.values())-half_bar_width, max(spines.values())+half_bar_width
        for p in branches:
            gap = bar_left-p['x']-p['w'] if p['x']+p['w']<=bar_left else p['x']-bar_right if p['x']>=bar_right else -1
            bar_gaps.append(dict(tag=p['tag'],gap_mm=gap))
    side_min = min((min(p['left_mm'],p['right_mm']) for p in margins),default=None)
    return dict(body_to_shell=margins, minimum_side_mm=side_min,
                side_policy_satisfied=side_min is not None and side_min>=policy['side_margin_mm'],
                main_to_branch_vertical_gap_mm=main_gap,
                branch_bottom_mm=min((p['y'] for p in branches),default=None),
                device_bottom_mm=min((p['y'] for p in inside),default=None),
                branch_to_busbar_edges=bar_gaps,
                basis='2D body envelopes and provisional busbar width; excludes terminals, cables and swept handles',
                compliance='requires_connection_and_manufacturer_review')

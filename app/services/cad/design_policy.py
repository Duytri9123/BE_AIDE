"""User cabinet layout policy; distinct from verified electrical clearance."""

def dimensions_for_current(current):
    if current is None or current < 100:
        return dict(top_gap_mm=None,side_margin_mm=None,status='needs_current_rule')
    return dict(top_gap_mm=150 if current<200 else 300 if current<300 else 400,
                side_margin_mm=150 if current>200 else 110,status='user_rule')

def check_fishbone(current):
    if current is not None and current>250:
        raise ValueError('Quy tắc thiết kế: đồng xương cá chỉ dùng khi CB chính <=250A; cần phương án phân phối khác')

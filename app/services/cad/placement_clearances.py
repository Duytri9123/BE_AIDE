"""Read per-face clearances from reviewed source evidence, not sheet margins."""
import math


def usable_region(bounds, source_item, face):
    rule=((source_item or {}).get('placement_rules') or {}).get(face) or {}
    if rule.get('verified') is not True or not rule.get('source_handles'):
        raise ValueError('Chưa xác nhận mép lắp đặt, hèm và khoảng dây cho mặt '+face)
    values=[rule.get(key) for key in ('left_mm','bottom_mm','right_mm','top_mm')]
    if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or v<0 for v in values):
        raise ValueError('Khoảng chừa mép có dữ liệu không hợp lệ: '+face)
    left,bottom,right,top=bounds
    l,b,r,t=values
    region=(left+l,bottom+b,right-r,top-t)
    if region[0]>=region[2] or region[1]>=region[3]:
        raise ValueError('Khoảng chừa mép làm hết vùng lắp thiết bị: '+face)
    return region


def device_gap(device, axis):
    rule=device.get('verified_placement_clearance') or {}
    if rule.get('verified') is True and rule.get('source_reference'):
        value=rule.get(axis+'_mm')
        if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>=0:
            return value
    # DIN modular adjacency is a layout convention only; thermal and terminal
    # checks remain separate release checks.
    if axis=='horizontal' and str(device.get('category') or '').upper() in ('MCB','RCBO','RCCB'):
        return 0
    raise ValueError('Chưa xác nhận khoảng '+axis+' cho '+str(device.get('tag') or device.get('name') or 'thiết bị'))

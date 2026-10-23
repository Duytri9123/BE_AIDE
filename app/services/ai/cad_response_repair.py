"""Retry malformed CAD envelopes without accepting a silently truncated BOM."""
import json,re
from app.services.ai.response_parser import ResponseParserService


def literal_values(response):
    keys='category|tag|spec|quantity|drawing_quantity|procurement_quantity|in_a|icu_ka|poles'
    pairs=re.findall(r'"('+keys+r')"\s*:\s*("(?:\\.|[^"\\])*"|null|-?\d+(?:\.\d+)?)',response)
    values={}
    for key,value in pairs:
        values.setdefault(key,[]).append(json.loads(value))
    return values


async def ensure_cad_response(response,repair):
    if ResponseParserService.parse_device_list(response):return response
    if not re.search(r'"category"\s*:',response or ''):
        raise ValueError('Phản hồi CAD chưa có danh sách thiết bị đọc được; chưa chốt BOM.')
    corrected=await repair('Chỉ sửa CÚ PHÁP JSON của phản hồi CAD dưới đây. Không đọc lại hay thay đổi thiết kế. '
        'Giữ nguyên toàn bộ thiết bị, thứ tự, tag, category, spec, các số lượng, dòng điện, số cực và khả năng cắt. '
        'Sửa đúng dấu đóng mảng/object; không trả một phần danh sách, không thêm thiết bị, không đổi tên khóa. '
        'Trả một JSON hoàn chỉnh, không markdown.\n'+response)
    if literal_values(response)!=literal_values(corrected):
        raise ValueError('Lượt sửa JSON đã thay đổi dữ liệu CAD nguồn; chưa chấp nhận kết quả bóc tách.')
    if not ResponseParserService.parse_device_list(corrected):
        raise ValueError('Chưa sửa được JSON CAD đầy đủ; chưa chốt BOM từ danh sách thiếu.')
    return corrected

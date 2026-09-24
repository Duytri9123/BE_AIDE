"""Shared classification for browsing, catalog entries and CAD source assets."""
import re
import unicodedata


def normalize(value):
    return ''.join(c for c in unicodedata.normalize('NFD', str(value).lower().replace('đ', 'd')) if unicodedata.category(c) != 'Mn')


RULES = [
    ('device', 'Biến tần', r'bien tan|\bvsd\b|\binverter\b|\batv\d'),
    ('device', 'Bộ nguồn DC', r'bo nguon dc|power supply|24vdc'),
    ('accessory', 'Bản lề', r'ban[- ]?le|^tv-h?bl|^hl0(?:03|11|12|35|36|44)'),
    ('accessory', 'Sứ và giá đỡ', r'^su[- ]?\d+|^su-canh|end stopper'),
    ('accessory', 'Cơ khí tủ', r'^(?:ecu|eku)\d|hex head screw|^nut$|chot canh|ga tai lieu|strut|thanh tieu chuan'),
    ('accessory', 'Quạt và lọc gió', r'q_fan|loc bui|louver'),
    ('accessory', 'Thanh đồng và đầu nối', r'^cos \d|^tc_ne'),
    ('accessory', 'Khóa tủ', r'lockjapan'),
    ('accessory', 'Cầu đấu', r'^cd_|^tb\d|^cts ?\d|^uk3n|teminal|terminer block|^tbdk$'),
    ('device', 'Biến dòng', r'^cml\d+a|^kde ?\d+a|^em4h0[3-7]'),
    ('device', 'Contactor', r'^mc[- ]?\d+a'),
    ('device', 'Thiết bị đóng cắt', r'^ab[snl]\(?n?\)?\d|^bkn |^ezc\d|^ls \d+ ?af'),
    ('device', 'Nút nhấn và còi', r'chuyen mach'),
    ('device', 'Đồng hồ và công tơ', r'^am-to$'),
    ('device', 'Ổ cắm', r'^ocam$'),
    ('device', 'Tụ bù và cuộn kháng', r'^tu \d+kvar'),
    ('accessory', 'Form tủ', r'^form tu|^mau tu'),
    ('accessory', 'Bản lề', r'ban le|banlela|bl012|bl036'),
    ('accessory', 'Khóa tủ', r'khoa|ms722|ms303|ms308|ms325'),
    ('accessory', 'Quạt và lọc gió', r'quat|\bfan\b|tam loc|filter'),
    ('accessory', 'Thanh đồng và đầu nối', r'busbar|thanh dong|cau n\+pe|dau cos|lug'),
    ('accessory', 'Cầu đấu', r'cau dau|domino|terminal|\btb[- ]|hanyong|\bhy[t]?[- ]'),
    ('accessory', 'Sứ và giá đỡ', r'su kep|su do|insulator|support'),
    ('accessory', 'Máng dây và ray DIN', r'mang nhua|mang day|din rail|ray din|duct'),
    ('accessory', 'Nhãn và mặt che', r'tem at|mac nhua|mica|canh bao|mat cong to|mat kinh'),
    ('accessory', 'Cơ khí tủ', r'bulon|bulong|\becu\b|tai cau|tai treo|moccau|mounting|tam ke|panel|gland'),
    ('device', 'Đèn báo', r'den bao|den (do|vang|xanh)|pilot|warning light'),
    ('device', 'Nút nhấn và còi', r'nut nhan|nut an|push|button|emergency|dung khan|\bcoi\b'),
    ('device', 'Cầu chì', r'cau chi|\bfuse\b'),
    ('device', 'Chống sét', r'chong set|\bspd\b'),
    ('device', 'Biến dòng', r'bien dong|\bct\b|\bemic\b|\bcml\b'),
    ('device', 'Đồng hồ và công tơ', r'dong ho|cong to|congto|meter|von-to|von-nho|am-nho'),
    ('device', 'Bộ điều khiển', r'dieu khien|ats|apfc|controller|logo'),
    ('device', 'Rơ le và timer', r'ro le|relay|timer|bao ve pha|\bmt[- ]?\d'),
    ('device', 'Tụ bù và cuộn kháng', r'tu kho|tu dau|tu bu|capacitor|cuon khang|reactor|nuintek|samwha'),
    ('device', 'Biến áp và ổn áp', r'bien ap|on ap|transformer'),
    ('device', 'Ổ cắm', r'o cam|socket'),
    ('device', 'Contactor', r'contactor|\bmc ?\d|lc1|\bctt\b'),
    ('device', 'Thiết bị đóng cắt', r'mccb|mcb|acb|rccb|rcbo|elcb|afdd|\bcb\b|\bls \d+af|\bn[fsxm][a-z0-9-]*\d'),
]


def classify(name, category=''):
    # Explicit source-table labels take priority over opaque block names.
    for text in (normalize(category), normalize(name)):
        for kind, group, pattern in RULES:
            if re.search(pattern, text):
                return {'kind': kind, 'group': group}
    return {'kind': 'unclassified', 'group': 'Chưa phân loại'}


def explicit_brands(text):
    key = normalize(text)
    brands = []
    for pattern, brand in [(r'\bls\b', 'LS'), (r'schneider|\bsc\b', 'Schneider Electric'),
                           (r'chint', 'Chint'), (r'idec', 'Idec'), (r'selec', 'Selec'),
                           (r'mikro', 'Mikro'), (r'nuintek', 'Nuintek'), (r'samwha', 'Samwha'),
                           (r'hanyong', 'Hanyong'), (r'\bemic\b', 'EMIC'), (r'hyundai', 'Hyundai'),
                           (r'mitsubishi', 'Mitsubishi'), (r'\babb\b', 'ABB'), (r'delab', 'Delab')]:
        if re.search(pattern, key): brands.append(brand)
    return brands

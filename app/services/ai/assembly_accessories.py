"""Engineering suggestions per assembly; never source evidence or priced items."""

SOURCES = [
    {'title': 'Schneider Electric – Star-delta assembly components',
     'url': 'https://www.se.com/uk/en/faqs/FA136856/'},
    {'title': 'ABB – Softstarter Handbook',
     'url': 'https://library.e.abb.com/public/6b4e1a3530814df0c12579bb0030e58b/1SFC132060M0201.pdf'},
    {'title': 'Schneider Electric – Altivar installation manual',
     'url': 'https://download.se.com/files?p_Doc_Ref=EAV64301&p_enDocType=User+guide'},
]


def propose_assembly_accessories(assembly_type, circuit, components, power_w=None, load=None):
    result = []
    present = {c.get('category') for c in components if isinstance(c, dict)}
    if any('bypass' in str(c.get('name') or '').lower() for c in components if isinstance(c, dict)):
        present.add('BYPASS_CONTACTOR')

    def add(category, name, quantity, reason, condition, selection):
        if category in present:
            return
        result.append(dict(category=category, name=name, quantity=quantity, unit='Cái',
                           quantity_basis='per_assembly', basis='engineering_recommendation',
                           status='proposal', included_in_total=False, part_number=None,
                           reason=reason, condition=condition, selection_note=selection))

    known = {'DOL', 'STAR_DELTA', 'REVERSING', 'SOFT_STARTER', 'VFD', 'ATS'}
    if assembly_type not in known:
        return []

    context = []
    if load:
        context.append(str(load))
    if power_w is not None:
        context.append(f'Công suất phụ tải {power_w:g} W')
    for key, label in [('motor_rated_current_a', 'Dòng động cơ (A)'),
                       ('motor_voltage_v', 'Điện áp động cơ (V)'),
                       ('control_voltage_v', 'Điện áp điều khiển (V)')]:
        if circuit.get(key) is not None:
            context.append(f'{label}: {circuit[key]}')

    add('CONTROL_PROTECTION', 'Bảo vệ mạch điều khiển (MCB hoặc cầu chì)', 1,
        'Bảo vệ dây và phần tử điều khiển.', 'Nếu chưa có bảo vệ riêng hoặc chưa dùng chung từ tủ.',
        'Chọn điện áp, số cực, dòng và khả năng cắt theo mạch; không chọn theo công suất động cơ đơn thuần.')
    add('CONTROL_POWER_SUPPLY', 'Nguồn hoặc biến áp điều khiển', None,
        'Cấp điện áp phù hợp cho bộ điều khiển và cuộn hút.', 'Chỉ bổ sung khi nguồn sẵn có không phù hợp.',
        'Chốt điện áp vào/ra, AC/DC và tổng tải điều khiển; kiểm tra nguồn dùng chung trong tủ.')
    add('TERMINAL_BLOCK', 'Cầu đấu động lực, điều khiển và PE', None,
        'Đấu nối nguồn, động cơ và tín hiệu ngoài.', 'Theo số đầu dây và cách bố trí thực tế.',
        'Chọn số cực, tiết diện và dòng chịu tải; không nhân đôi vật tư đã nằm trong gói phụ kiện tủ.')
    add('RUN_INDICATOR', 'Đèn báo chạy', 1,
        'Hiển thị trạng thái vận hành của cụm.', 'Nếu cần hiển thị tại tủ và chưa dùng HMI hoặc đèn dùng chung.',
        'Lấy tín hiệu xác nhận chạy phù hợp; điện áp đèn theo mạch điều khiển.')
    add('FAULT_INDICATOR', 'Đèn báo lỗi / quá tải', 1,
        'Hiển thị sự cố của cụm.', 'Nếu có tín hiệu lỗi và yêu cầu hiển thị tại tủ.',
        'Xác định tiếp điểm báo lỗi và điện áp đèn theo thiết bị thực tế.')

    if assembly_type in {'DOL', 'STAR_DELTA', 'REVERSING'}:
        add('AUX_CONTACT', 'Tiếp điểm phụ cho tự giữ, liên động và báo trạng thái', None,
            'Bổ sung các tiếp điểm NO/NC theo logic điều khiển.', 'Chỉ mua thêm khi tiếp điểm tích hợp không đủ.',
            'Chốt số NO/NC và mã contactor; phụ kiện phải đúng dòng thiết bị và kiểu lắp.')
        add('COIL_SUPPRESSOR', 'Bộ dập xung cuộn hút contactor', None,
            'Giảm xung điện khi nhả cuộn hút.', 'Nếu đầu ra điều khiển hoặc nhà sản xuất yêu cầu.',
            'Chọn theo điện áp AC/DC, loại cuộn hút và hướng dẫn của contactor.')
    if assembly_type in {'STAR_DELTA', 'REVERSING'}:
        add('MECHANICAL_INTERLOCK', 'Bộ liên động cơ khí contactor', 1,
            'Ngăn cặp contactor đối nghịch đóng đồng thời.', 'Theo cấu trúc mạch sao–tam giác hoặc thuận–nghịch.',
            'Đúng cặp contactor, cỡ khung và khoảng cách lắp; phối hợp liên động điện.')
    if assembly_type == 'STAR_DELTA':
        add('STAR_DELTA_WIRING_KIT', 'Bộ thanh nối / dây nối sao–tam giác', 1,
            'Đấu nối cụm ba contactor theo sơ đồ.', 'Nếu dùng bộ kit thay cho dây đấu tự gia công.',
            'Chọn theo bố trí contactor và dòng; kiểm tra timer/liên động đã có trong bộ kit.')
    if assembly_type == 'SOFT_STARTER' and circuit.get('bypass_integrated') is not True:
        add('BYPASS_CONTACTOR', 'Contactor bypass ngoài', 1,
            'Cho dòng chạy qua nhánh bypass sau khi khởi động.',
            'Chỉ khi model không tích hợp bypass và phương án thiết kế yêu cầu bypass ngoài.',
            'Chọn theo dòng động cơ, sơ đồ phối hợp bảo vệ và tín hiệu điều khiển của model.')
    if assembly_type == 'VFD':
        add('EMC_TERMINATION', 'Kẹp tiếp địa màn chắn cáp / phụ kiện EMC', None,
            'Đấu nối màn chắn cáp theo yêu cầu EMC.', 'Theo loại cáp và hướng dẫn lắp đặt của biến tần.',
            'Chốt số cáp, đường kính và phương án nối đất.')
        if circuit.get('speed_control_mode') == 'potentiometer':
            add('SPEED_POTENTIOMETER', 'Biến trở đặt tốc độ', 1,
                'Đặt tốc độ tại tủ.', 'Đầu vào yêu cầu điều chỉnh tốc độ bằng biến trở.',
                'Chọn điện trở và sơ đồ chân theo ngõ vào analog của biến tần.')
        add('DRIVE_FILTER', 'Cuộn kháng / bộ lọc cho biến tần', None,
            'Đánh giá chất lượng nguồn và tác động của cáp động cơ.',
            'Chỉ chọn sau khi kiểm tra nguồn, chiều dài cáp, động cơ và yêu cầu của nhà sản xuất.',
            'Phân biệt kháng đầu vào, kháng đầu ra, lọc EMC và dV/dt; không coi chúng là một loại thay thế nhau.')
    if assembly_type == 'ATS':
        add('SOURCE_MONITOR', 'Rơ le giám sát nguồn', None,
            'Giám sát điều kiện nguồn cho chuyển đổi.', 'Chỉ khi bộ điều khiển ATS chưa có chức năng tương ứng.',
            'Chọn số nguồn, số pha, ngưỡng và thời gian; kiểm tra chức năng có sẵn của ATS.')
        add('ATS_INTERLOCK', 'Phụ kiện liên động chuyển nguồn', 1,
            'Đảm bảo vận hành chuyển nguồn đúng cấu trúc thiết bị.',
            'Theo bộ chuyển nguồn hoặc cặp thiết bị đóng cắt đã chọn; kiểm tra bộ tích hợp.',
            'Dùng đúng bộ liên động của hãng và sơ đồ vận hành được thiết kế.')

    for row in result:
        row['input_context'] = context
    return result

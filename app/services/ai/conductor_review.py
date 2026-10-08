"""Per-connection review: neither current nor CAD geometry establishes a conductor."""


def connection_requirements(devices):
    result=[]
    for d in devices:
        tag=d.get('tag') or d.get('name') or '?'
        cat=str(d.get('category') or '').upper()
        if cat in ('MCB','MCCB','ACB','RCBO','RCCB'):
            roles=[('LINE','Nguồn vào'),('LOAD','Ra tải')]
        elif cat in ('LIGHT','METER','SELECTOR','FUSE','FUSE_HOLDER'):
            roles=[('CONTROL_MEASUREMENT','Đo lường / điều khiển')]
        elif cat in ('PE','N'):
            roles=[(cat,'Liên kết '+cat)]
        else:continue
        for terminal,role in roles:
            result.append(dict(device_tag=tag,terminal=terminal,role=role,
                knowledge_ref='data/CatalogTB/cb_conductor_knowledge.json',
                upstream=d.get('upstream_device'),downstream=d.get('downstream_device'),
                conductor_type=None,material=None,section_mm2=None,length_m=None,
                status='needs_connection_design',auto_assigned=False,
                required_information=['Cọc và giới hạn dây/thanh của model','Từ/đến và pha/N/PE',
                    'Dòng tải và bảo vệ đoạn dây','Điều kiện lắp/nhiệt/nhóm dây',
                    'Ngắn mạch, sụt áp và chiều dài','Đầu cốt, bán kính uốn và lực siết'],
                selection_options=['Dây lực cách điện','Thanh đồng chính + dây nhánh','Thanh lược hãng','Đồng xương cá gia công có kiểm chứng']
                    if terminal=='LINE' else ['Dây/cáp phù hợp cọc thực tế'],
                rule='Cáp ghi trên sơ đồ của tuyến ngoài tủ không tự xác định dây nhảy nội bộ. Không suy tiết diện từ A hoặc hình CAD.'))
    return result

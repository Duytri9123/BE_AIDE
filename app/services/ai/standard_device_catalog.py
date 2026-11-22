"""Standard device catalog suggestions for missing electrical components.

Provides industry-standard SKUs from major brands (Schneider, LS, Chint, Panasonic, Mikro, Mitsubishi)
when the internal database does not have an exact pricebook entry.
"""
from typing import Dict, List, Any


def get_standard_candidates(category: str, spec: str = "", name: str = "", poles: int = None, in_a: float = None, icu_ka: float = None) -> Dict[str, List[Dict[str, Any]]]:
    """Return standard market candidate models grouped by brand for a given device."""
    cat = str(category or "").upper().strip()
    spec_clean = str(spec or "").upper().strip()
    name_clean = str(name or "").upper().strip()
    full_text = f"{cat} {name_clean} {spec_clean}"
    
    candidates: Dict[str, List[Dict[str, Any]]] = {}

    # 1. RCBO / Aptomat chống dòng rò
    if "RCBO" in full_text or ("CHỐNG DÒNG RÒ" in full_text and "RCBO" in full_text) or (cat in ("RCBO", "RCCB")):
        amps = int(in_a) if in_a else (16 if "16A" in full_text else (25 if "25A" in full_text else (20 if "20A" in full_text else 16)))
        p = int(poles) if poles else (4 if ("4P" in full_text or "4 CỰC" in full_text) else 2)
        
        if p == 4:
            candidates["Schneider"] = [{
                "sku": f"A9D114{amps:02d}",
                "name": f"Acti9 iC60H RCBO 4P {amps}A 30mA 10kA",
                "brand": "Schneider",
                "icu_ka": 10.0,
                "price": 1450000,
                "source": "standard_catalog",
                "rating_complete": True,
                "auto_selectable": True,
                "reason": f"RCBO 4P {amps}A 30mA Schneider Acti9 chuẩn bảo vệ chống rò và quá tải 3 pha."
            }]
            candidates["Chint"] = [{
                "sku": f"NXBLE-32 4P {amps}A 30mA",
                "name": f"RCBO Chint NXBLE-32 4P {amps}A 30mA 6kA",
                "brand": "Chint",
                "icu_ka": 6.0,
                "price": 380000,
                "source": "standard_catalog",
                "rating_complete": True,
                "auto_selectable": True,
                "reason": f"RCBO 4P {amps}A 30mA Chint NXBLE-32 kinh tế."
            }]
        else:
            candidates["Schneider"] = [
                {
                    "sku": f"A9D316{amps:02d}",
                    "name": f"Acti9 iDPN N Vigi 1P+N {amps}A 30mA 6kA",
                    "brand": "Schneider",
                    "icu_ka": 6.0,
                    "price": 680000,
                    "source": "standard_catalog",
                    "rating_complete": True,
                    "auto_selectable": True,
                    "reason": f"RCBO 2P (1P+N) {amps}A 30mA Schneider Acti9 iDPN N Vigi cao cấp."
                },
                {
                    "sku": f"EZ9D346{amps:02d}",
                    "name": f"Easy9 RCBO 1P+N {amps}A 30mA 4.5kA",
                    "brand": "Schneider",
                    "icu_ka": 4.5,
                    "price": 420000,
                    "source": "standard_catalog",
                    "rating_complete": True,
                    "auto_selectable": True,
                    "reason": f"RCBO 2P (1P+N) {amps}A 30mA Schneider Easy9 kinh tế."
                }
            ]
            candidates["LS Electric"] = [{
                "sku": f"32KGRc 2P {amps}A 30mA",
                "name": f"RCBO LS 32KGRc 2P {amps}A 30mA 2.5kA",
                "brand": "LS Electric",
                "icu_ka": 4.5,
                "price": 320000,
                "source": "standard_catalog",
                "rating_complete": True,
                "auto_selectable": True,
                "reason": f"RCBO LS 32KGRc 2P {amps}A 30mA tiêu chuẩn dân dụng và thương mại."
            }]
            candidates["Mitsubishi"] = [{
                "sku": f"BV-DN 2P {amps}A 30mA",
                "name": f"RCBO Mitsubishi BV-DN 2P {amps}A 30mA 4.5kA",
                "brand": "Mitsubishi",
                "icu_ka": 4.5,
                "price": 550000,
                "source": "standard_catalog",
                "rating_complete": True,
                "auto_selectable": True,
                "reason": f"RCBO Mitsubishi BV-DN 2P {amps}A 30mA 4.5kA chuẩn Nhật Bản."
            }]
            candidates["Chint"] = [{
                "sku": f"NXBLE-32 2P {amps}A 30mA",
                "name": f"RCBO Chint NXBLE-32 2P {amps}A 30mA 6kA",
                "brand": "Chint",
                "icu_ka": 6.0,
                "price": 185000,
                "source": "standard_catalog",
                "rating_complete": True,
                "auto_selectable": True,
                "reason": f"RCBO Chint NXBLE-32 2P {amps}A 30mA 6kA tối ưu chi phí."
            }]

    # 2. Timer / Rơ le thời gian / Công tắc hẹn giờ
    elif "TIMER" in full_text or "THỜI GIAN" in full_text or cat == "TIMER":
        candidates["Panasonic"] = [
            {
                "sku": "TB38809NE7",
                "name": "Công tắc thời gian Panasonic 24h TB38809NE7 (pin chờ 300h)",
                "brand": "Panasonic",
                "price": 520000,
                "source": "standard_catalog",
                "rating_complete": True,
                "auto_selectable": True,
                "reason": "Bộ hẹn giờ 24h Panasonic TB38809NE7 cơ có pin dự phòng 300h khi mất điện, tải tiếp điểm 20A."
            },
            {
                "sku": "TB35609NE7",
                "name": "Công tắc thời gian Panasonic điện tử TB35609NE7",
                "brand": "Panasonic",
                "price": 890000,
                "source": "standard_catalog",
                "rating_complete": True,
                "auto_selectable": True,
                "reason": "Bộ hẹn giờ kỹ thuật số tuần hoàn Panasonic TB35609NE7 chuẩn thương mại."
            }
        ]
        candidates["Schneider"] = [{
            "sku": "CCT15443",
            "name": "Rơ le thời gian kỹ thuật số Schneider Acti9 IHP 1C (CCT15443)",
            "brand": "Schneider",
            "price": 1250000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "Schneider Acti9 IHP 1 kênh gắn ray DIN 35mm, lập trình 24h/7 ngày, độ chính xác cao."
        }]
        candidates["Chint"] = [{
            "sku": "KG316T",
            "name": "Bộ hẹn giờ kỹ thuật số Chint KG316T 220VAC",
            "brand": "Chint",
            "price": 140000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "Bộ hẹn giờ Chint KG316T 220VAC 25A gắn thanh ray DIN, giá thành kinh tế."
        }]

    # 3. Cuộn cắt / Shunt Trip (S/T)
    elif "CUỘN CẮT" in full_text or "CUON CAT" in full_text or "SHUNT" in full_text or "S/T" in full_text:
        candidates["Schneider"] = [{
            "sku": "LV429387",
            "name": "Cuộn cắt Schneider MX 220-240VAC cho MCCB Compact NSX100-250",
            "brand": "Schneider",
            "price": 850000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "Cuộn Shunt Trip MX 220-240VAC lắp trong MCCB tổng Schneider NSX/CVS 100-250A."
        }]
        candidates["LS Electric"] = [{
            "sku": "SHT-160 200-240VAC",
            "name": "Cuộn cắt LS Shunt Trip SHT-160 cho MCCB TS160/TD160",
            "brand": "LS Electric",
            "price": 420000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "Cuộn Shunt Trip LS SHT-160 200-240VAC lắp trong MCCB Metasol/Susol 100-160A."
        }]
        candidates["Mitsubishi"] = [{
            "sku": "SHT-N05 200-240VAC",
            "name": "Cuộn cắt Mitsubishi SHT 200-240VAC cho MCCB NF125/NF160",
            "brand": "Mitsubishi",
            "price": 750000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "Cuộn Shunt Trip Mitsubishi SHT 200-240VAC tương thích MCCB tổng 150A."
        }]

    # 4. Rơ le rò đất (ELR / Earth Fault Relay) / Chạm đất
    elif "CHẠM ĐẤT" in full_text or "CHAM DAT" in full_text or "RÒ ĐẤT" in full_text or "RO DAT" in full_text or "ELR" in full_text or "EF" in full_text:
        candidates["Mikro"] = [{
            "sku": "NX301A-240A",
            "name": "Rơ le bảo vệ dòng rò chạm đất Mikro NX301A-240A",
            "brand": "Mikro",
            "price": 950000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "Rơ le bảo vệ dòng rò chạm đất Mikro NX301A, dải chỉnh 0.1-30A, gắn mặt tủ hoặc thanh ray."
        }]
        candidates["Delab"] = [{
            "sku": "ELR-300",
            "name": "Rơ le rò đất Delab ELR-300 220VAC",
            "brand": "Delab",
            "price": 820000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "Rơ le rò đất Delab ELR-300 chỉnh dòng và thời gian tác động ngắt Shunt Trip."
        }]
        candidates["Schneider"] = [{
            "sku": "Vigirex RH99M",
            "name": "Rơ le bảo vệ dòng rò Schneider Vigirex RH99M 220VAC",
            "brand": "Schneider",
            "price": 2800000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "Rơ le bảo vệ dòng rò cao cấp Schneider Vigirex RH99M chuẩn công nghiệp."
        }]

    # 5. Biến dòng thứ tự không (ZCT)
    elif "BIẾN DÒNG THỨ TỰ KHÔNG" in full_text or "THỨ TỰ KHÔNG" in full_text or "ZCT" in full_text:
        candidates["Mikro"] = [{
            "sku": "ZCT-080",
            "name": "Biến dòng thứ tự không Mikro ZCT-080 (đường kính trong phi 80mm)",
            "brand": "Mikro",
            "price": 620000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "Biến dòng thứ tự không ZCT Mikro phi 80mm luồn cáp nguồn 4 sợi 50mm2 vào MCCB tổng."
        }]
        candidates["Delab"] = [{
            "sku": "ZCT-120",
            "name": "Biến dòng thứ tự không Delab ZCT-120 (đường kính phi 120mm)",
            "brand": "Delab",
            "price": 750000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "Biến dòng ZCT Delab phi 120mm luồn dây cáp nguồn tiết diện lớn."
        }]

    # 6. MCCB tổng (150A 36kA 3P)
    elif "MCCB" in full_text and ("150A" in full_text or "160A" in full_text or in_a in (150, 160)):
        candidates["Schneider"] = [{
            "sku": "C16F3TM160",
            "name": "MCCB Schneider ComPacT NSX160F 3P 36kA 160A TMD",
            "brand": "Schneider",
            "icu_ka": 36.0,
            "price": 3450000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "MCCB Schneider NSX160F 3P 36kA chỉnh nhiệt 112-160A chuẩn aptomat tổng."
        }]
        candidates["LS Electric"] = [{
            "sku": "TS160N 3P 150A 36kA",
            "name": "MCCB LS Susol TS160N 3P 150A 36kA",
            "brand": "LS Electric",
            "icu_ka": 36.0,
            "price": 1850000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "MCCB LS Susol TS160N 3P 150A 36kA kinh tế, tin cậy."
        }]
        candidates["Mitsubishi"] = [{
            "sku": "NF160-SGV 3P 150A 36kA",
            "name": "MCCB Mitsubishi NF160-SGV 3P 150A 36kA",
            "brand": "Mitsubishi",
            "icu_ka": 36.0,
            "price": 3100000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "MCCB Mitsubishi NF160-SGV 3P 150A 36kA chuẩn Nhật Bản."
        }]

    # 7. MCB 1P / 3P
    elif cat == "MCB" or "MCB" in full_text or "APTOMAT NHÁNH" in full_text or "APTOMAT TÉP" in full_text:
        amps = int(in_a) if in_a else (20 if "20A" in full_text else (16 if "16A" in full_text else (10 if "10A" in full_text else 16)))
        p = int(poles) if poles else (3 if ("3P" in full_text or "3 CỰC" in full_text) else 1)
        
        if p == 3:
            candidates["Schneider"] = [{
                "sku": f"A9F743{amps:02d}",
                "name": f"Acti9 iC60N MCB 3P {amps}A 6kA",
                "brand": "Schneider",
                "icu_ka": 6.0,
                "price": 420000,
                "source": "standard_catalog",
                "rating_complete": True,
                "auto_selectable": True,
                "reason": f"MCB 3P {amps}A 6kA Schneider Acti9 iC60N."
            }]
            candidates["LS Electric"] = [{
                "sku": f"BKN 3P {amps}A 6kA",
                "name": f"MCB LS BKN 3P {amps}A 6kA",
                "brand": "LS Electric",
                "icu_ka": 6.0,
                "price": 220000,
                "source": "standard_catalog",
                "rating_complete": True,
                "auto_selectable": True,
                "reason": f"MCB 3P {amps}A 6kA LS BKN."
            }]
        else:
            candidates["Schneider"] = [{
                "sku": f"A9F741{amps:02d}",
                "name": f"Acti9 iC60N MCB 1P {amps}A 6kA",
                "brand": "Schneider",
                "icu_ka": 6.0,
                "price": 140000,
                "source": "standard_catalog",
                "rating_complete": True,
                "auto_selectable": True,
                "reason": f"MCB 1P {amps}A 6kA Schneider Acti9 iC60N."
            }]
            candidates["LS Electric"] = [{
                "sku": f"BKN 1P {amps}A 6kA",
                "name": f"MCB LS BKN 1P {amps}A 6kA",
                "brand": "LS Electric",
                "icu_ka": 6.0,
                "price": 75000,
                "source": "standard_catalog",
                "rating_complete": True,
                "auto_selectable": True,
                "reason": f"MCB 1P {amps}A 6kA LS BKN chuẩn kinh tế."
            }]

    # 8. Cầu chì đo lường (FUSE 2A / 500V)
    elif "CẦU CHÌ" in full_text or cat in ("FUSE", "FUSE_BASE", "FUSE_LINK"):
        candidates["Chint"] = [{
            "sku": "RT28-32 2A",
            "name": "Cầu chì hạ thế Chint RT28-32 (vỏ + ruột chì ống 10x38 2A)",
            "brand": "Chint",
            "price": 25000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "Cầu chì bảo vệ mạch đo lường volt/đèn báo pha tủ điện."
        }]
        candidates["Schneider"] = [{
            "sku": "DF2BN02",
            "name": "Cầu chì tép Schneider TeSys DF 10x38mm 2A",
            "brand": "Schneider",
            "price": 95000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "Cầu chì bảo vệ mạch điều khiển & đo lường Schneider cao cấp."
        }]

    # 9. Đèn báo pha (INDICATOR LIGHT LED 220V)
    elif "ĐÈN BÁO" in full_text or "BÁO PHA" in full_text or cat in ("LIGHT", "PILOT_LIGHT", "INDICATOR"):
        candidates["Chint"] = [{
            "sku": "ND16-22D 220VAC",
            "name": "Đèn báo pha LED Chint ND16-22D phi 22 220VAC (Đỏ/Vàng/Xanh)",
            "brand": "Chint",
            "price": 22000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "Đèn báo pha LED 220V mặt cánh tủ hạ thế."
        }]
        candidates["Schneider"] = [{
            "sku": "XB7EV08MP",
            "name": "Đèn báo pha Schneider Harmony Easy XA2 phi 22 220VAC LED",
            "brand": "Schneider",
            "price": 85000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "Đèn báo pha Schneider chuẩn công nghiệp độ bền cao."
        }]

    # 10. Chuyển mạch đo điện áp (VOLT SELECTOR SWITCH)
    elif "CHUYỂN MẠCH" in full_text or cat in ("SELECTOR", "VOLT_SELECTOR", "CAM_SWITCH"):
        candidates["Chint"] = [{
            "sku": "LW26-20/3",
            "name": "Chuyển mạch đo điện áp Chint LW26-20 (7 vị trí đo pha & dây)",
            "brand": "Chint",
            "price": 95000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "Chuyển mạch Volt 7 vị trí đo điện áp dây (RS, ST, TR) và điện áp pha (RN, SN, TN, 0)."
        }]
        candidates["Schneider"] = [{
            "sku": "K1F003NLH",
            "name": "Chuyển mạch điện áp Schneider Harmony K 7 vị trí 3 pha + trung tính",
            "brand": "Schneider",
            "price": 480000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "Chuyển mạch chọn vôn Schneider Harmony K cao cấp."
        }]

    # 11. Đồng hồ đo điện áp (VOLTMETER 0-500V)
    elif "ĐỒNG HỒ" in full_text and ("VOLT" in full_text or "ĐIỆN ÁP" in full_text or cat in ("VOLTMETER", "METER")):
        candidates["Emic"] = [{
            "sku": "V96 0-500V",
            "name": "Đồng hồ đo điện áp kim Emic V96 dải đo 0-500V AC (kích thước 96x96)",
            "brand": "Emic",
            "price": 180000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "Đồng hồ Volt kim 0-500V Emic gắn mặt cánh tủ phổ biến."
        }]
        candidates["Mikro"] = [{
            "sku": "MVM-500",
            "name": "Đồng hồ đo vôn điện tử Mikro MVM-500 dải đo 0-500V",
            "brand": "Mikro",
            "price": 450000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "Đồng hồ Volt hiển thị LED kỹ thuật số chính xác."
        }]

    # 12. Biến dòng đo lường (CT - Current Transformer)
    elif "BIẾN DÒNG" in full_text or cat in ("CT", "CURRENT_TRANSFORMER"):
        candidates["Emic"] = [{
            "sku": "CT-150/5A",
            "name": "Biến dòng hạ thế Emic tròn luồn cáp tỷ số 150/5A 5VA Cấp 0.5",
            "brand": "Emic",
            "price": 160000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "Biến dòng đo lường tỷ số 150/5A đồng bộ với ampe kế và MCCB 150A."
        }]
        candidates["Mikro"] = [{
            "sku": "MS-30 150/5A",
            "name": "Biến dòng đo lường Mikro MS-30 tỷ số 150/5A Cấp 1.0",
            "brand": "Mikro",
            "price": 220000,
            "source": "standard_catalog",
            "rating_complete": True,
            "auto_selectable": True,
            "reason": "Biến dòng đo lường Mikro dạng khối nhỏ gọn."
        }]

    return candidates


def enrich_device_with_standard_candidates(device: Any) -> None:
    """Enrich a device candidate with standard catalog suggestions if missing."""
    existing = getattr(device, 'catalog_candidates', None) or {}
    if existing and any(len(rows) > 0 for rows in existing.values()):
        return

    cat = getattr(device, 'category', '') or ''
    spec = getattr(device, 'spec', '') or ''
    name = getattr(device, 'name', '') or ''
    poles = getattr(device, 'poles', None)
    in_a = getattr(device, 'in_a', None)
    icu_ka = getattr(device, 'icu_ka', None)

    standard = get_standard_candidates(cat, spec, name, poles, in_a, icu_ka)
    if standard:
        merged = dict(existing)
        for brand, rows in standard.items():
            merged.setdefault(brand, []).extend(rows)
        device.catalog_candidates = merged

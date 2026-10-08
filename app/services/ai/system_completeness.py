"""Evidence-based review; missing evidence never adds procurement items."""
from collections import defaultdict
import re
import unicodedata


def review_system(devices):
    groups = defaultdict(list)
    for raw in devices:
        d = raw.model_dump() if hasattr(raw, "model_dump") else dict(raw)
        groups[str(d.get("panel_code") or "CHUA_XAC_DINH")].append(d)
    issues, clusters = [], []

    def issue(panel, tag, title, detail, *, evidence=None, technical_reference=None,
              recommendation=None, required_information=None, severity="warning", certainty="missing_data"):
        targets = [d for d in groups[panel] if str(d.get("tag") or d.get("name") or "Thiết bị") == tag]
        source = targets[0] if len(targets) == 1 else {}
        issues.append(dict(panel_code=panel, tag=tag, title=title, detail=detail,
                           description=detail, evidence=evidence or [],
                           reason=detail, severity=severity, certainty=certainty,
                           source_filename=source.get("source_filename"), source_page=source.get("source_page"),
                           box_2d=source.get("box_2d"),
                           recommendation=recommendation or "Đối chiếu vùng liên quan trên bản vẽ nguồn và cập nhật dữ liệu đã xác nhận.",
                           required_information=required_information or [],
                           review_request=f"Rà soát {title} tại tủ {panel}, ký hiệu {tag}. Nêu căn cứ nguồn, nguyên nhân, hướng xử lý và dữ liệu còn thiếu; không tự thay đổi thiết kế hoặc thêm vật tư chưa xác nhận.",
                           technical_reference=technical_reference or [],
                           status="ATTENTION", badge="Cần đối chiếu nguồn"))

    for panel, members in groups.items():
        def source_ref(d):
            parts = [str(d.get("source_filename") or "").strip(), str(d.get("tag") or "").strip()]
            if d.get("source_page") is not None:
                parts.append(f"trang {d['source_page']}")
            return ", ".join(part for part in parts if part) or "chưa có vị trí nguồn"

        ct_devices = [d for d in members if str(d.get("category") or "").upper() in {"CT", "CURRENT_TRANSFORMER"}
                      or re.search(r"\b(?:CT|3XCT|3CT)\b|biến dòng", str(d.get("name") or "") + " " + str(d.get("spec") or ""), re.I)]
        ammeters = [d for d in members if re.search(r"ampe|ammeter|\bampe kế\b", str(d.get("name") or ""), re.I)
                    or str(d.get("tag") or "").upper() in {"A", "AM"}]
        selectors = [d for d in members if str(d.get("tag") or "").upper() == "AS"
                     or re.search(r"chọn dòng|ammeter selector", str(d.get("name") or ""), re.I)]
        if ct_devices and ammeters:
            ct_count = sum(int(d.get("procurement_quantity") or d.get("quantity") or 1) for d in ct_devices)
            if ct_count == 3 and selectors and len(ammeters) > 1:
                issue(panel, "AS/CT", "Kiểm tra số lượng ampe kế",
                      f"Có 3 CT và công tắc AS nhưng bóc {len(ammeters)} ampe kế. Kiểm tra ký hiệu A trên ảnh: {source_ref(ammeters[0])}. Ba CT không tự tạo ba ampe kế.",
                      evidence=[source_ref(ct_devices[0]), source_ref(selectors[0]), source_ref(ammeters[0])],
                      technical_reference=["https://iportal.se.com/Contents/docs/SQD-METSECT5MD080_CATALOGUE.PDF"])
            ratios = []
            for ct in ct_devices:
                match = re.search(r"(\d+(?:[.,]\d+)?)\s*/\s*5\s*A?", str(ct.get("spec") or ""), re.I)
                if match:
                    ratios.append(float(match.group(1).replace(",", ".")))
            for meter in ammeters:
                match = re.search(r"0\s*[-–]\s*(\d+(?:[.,]\d+)?)\s*A", str(meter.get("spec") or ""), re.I)
                if match and ratios and float(match.group(1).replace(",", ".")) not in ratios:
                    issue(panel, str(meter.get("tag") or "A"), "Thang ampe kế chưa khớp CT",
                          f"CT ghi tỷ số {ratios[0]:g}/5 A ({source_ref(ct_devices[0])}); ampe kế ghi {match.group(0)} ({source_ref(meter)}). Kiểm tra thang hiển thị hoặc cấu hình đồng hồ trước khi mua.",
                          evidence=[source_ref(ct_devices[0]), source_ref(meter)],
                          certainty="suspected",
                          recommendation="Xác minh đồng hồ dùng thang cố định hay cấu hình tỷ số CT; hiệu chỉnh hoặc chọn lại thang phù hợp khi xác nhận sai.",
                          required_information=["Tỷ số CT thực tế", "Loại và cấu hình đồng hồ"],
                          technical_reference=["https://www.se.com/us/en/faqs/FA125574/"])

        motor_feeders = [d for d in members if str(d.get("category") or "").upper() in {"MCB", "MCCB"}
                         and re.search(r"bơm|máy khuấy|động cơ|motor|máy thổi", " ".join(
                             str(d.get(k) or "") for k in ("connected_load", "downstream_device", "notes")), re.I)]
        motor_protection = {"CONTACTOR", "OVERLOAD", "THERMAL_RELAY", "MPCB", "MOTOR_PROTECTION", "VFD", "SOFT_STARTER"}
        if motor_feeders and not any(str(d.get("category") or "").upper() in motor_protection for d in members):
            sample = motor_feeders[0]
            issue(panel, str(sample.get("tag") or ""), "Chưa thấy mạch khởi động và bảo vệ động cơ",
                  f"Có {len(motor_feeders)} lộ MCB/MCCB ghi tải động cơ; ví dụ {source_ref(sample)}. Đối chiếu sơ đồ điều khiển và tủ tại máy để xác định contactor/bảo vệ quá tải; chưa cộng vào BOM.",
                  evidence=[source_ref(sample)],
                  technical_reference=["https://www.se.com/eg/en/download/document/LVED250601EN/"])

        tags = {str(d.get("tag")) for d in members if d.get("tag")}
        by_tag = defaultdict(list)
        for d in members:
            if d.get("tag"):
                by_tag[str(d["tag"])].append(d)
        for tag, repeated in by_tag.items():
            if len(repeated) > 1:
                issue(panel, tag, "Ký hiệu thiết bị bị trùng",
                      f"Có {len(repeated)} dòng cùng ký hiệu {tag} trong tủ {panel}; có thể là tham chiếu nhiều trang hoặc bóc tách trùng.",
                      evidence=[source_ref(d) for d in repeated], certainty="observed",
                      recommendation="Phân biệt thiết bị thực và tham chiếu trước khi gộp hoặc loại dòng.",
                      required_information=["Trang nguồn và vị trí của từng ký hiệu trùng"])
        # Only exact, unambiguous tag connections can establish a cycle.
        visited, cycles = set(), set()
        for start in by_tag:
            path, current = [], start
            while current in by_tag and len(by_tag[current]) == 1 and current not in visited:
                if current in path:
                    cycle = path[path.index(current):]
                    identity = tuple(sorted(cycle))
                    if identity not in cycles:
                        cycles.add(identity)
                        issue(panel, current, "Liên kết nguồn tạo vòng",
                              "Dữ liệu liên kết tạo vòng: " + " → ".join(cycle + [current]) + ". Cần phân biệt lỗi nhận diện với mạch chuyển nguồn/vòng có chủ đích.",
                              evidence=[source_ref(by_tag[t][0]) for t in cycle], certainty="suspected",
                              recommendation="Kiểm tra chiều cấp nguồn, điểm nối và liên động; sửa quan hệ bóc tách khi xác nhận đọc sai.",
                              required_information=["Sơ đồ nguồn và trạng thái đóng/mở của thiết bị liên quan"])
                    break
                path.append(current)
                current = str(by_tag[current][0].get("upstream_device") or "")
            visited.update(path)
        for d in members:
            tag = str(d.get("tag") or d.get("name") or "Thiết bị")
            text = " ".join(str(d.get(k) or "") for k in ("name", "spec", "electrical_function")).lower()
            cat = str(d.get("category") or "").upper()
            selected = (d.get("catalog_matches") or {}).get(d.get("brand"))
            if isinstance(selected, dict) and selected.get("meets_icu") is False:
                issue(panel, tag, "Mã đề xuất chưa đáp ứng khả năng cắt",
                      f"Catalog {d.get('brand') or ''} {selected.get('sku') or ''} ghi {selected.get('icu')} kA; yêu cầu bóc tách {d.get('icu_ka')} kA.",
                      evidence=[source_ref(d)], severity="critical", certainty="observed",
                      recommendation="Loại mã này khỏi lựa chọn chốt; đối chiếu khả năng cắt ở đúng điện áp hoặc phối hợp dự phòng được nhà sản xuất xác nhận.",
                      required_information=["Dòng ngắn mạch tại điểm lắp", "Điện áp làm việc", "Tài liệu phối hợp của nhà sản xuất"],
                      technical_reference=["https://www.electrical-installation.org/enwiki/Selection_of_a_circuit-breaker"])
            children = d.get("accompanying_accessories") or []
            observed, pending = [], []
            for child in children:
                if not isinstance(child, dict):
                    continue
                evidence = child.get("evidence") or child.get("source_reference") or child.get("sld_evidence")
                (observed if evidence else pending).append(child)
            for child in d.get("inferred_components") or []:
                if isinstance(child, dict):
                    pending.append(child)
            if children or pending or " với " in text or " và " in text:
                clusters.append(dict(panel_code=panel, parent_tag=tag, name=d.get("name"),
                                     observed_components=observed, review_components=pending,
                                     status="needs_review" if pending or not observed else "source_evidence_present"))
            if pending:
                issue(panel, tag, "Thành phần cụm chưa có bằng chứng", "Xác nhận thành phần và số lượng trên bản vẽ; chưa tự cộng các đề xuất vào BOM.")
            if ("ampe" in text and ("as" in text or "chuyển mạch" in text)) or ("volt" in text and ("vs" in text or "chuyển mạch" in text)):
                if not observed:
                    issue(panel, tag, "Đồng hồ và chuyển mạch đang gộp", "Cần xác định mã, số lượng và phạm vi bộ; tách đồng hồ/chuyển mạch thành vật tư riêng nếu mua rời.")
            if cat in {"MCB", "MCCB", "ACB", "RCBO", "RCCB"}:
                missing = [k for k in ("in_a", "poles") if not d.get(k)]
                if cat != "RCCB" and not d.get("icu_ka"):
                    missing.append("icu_ka")
                if missing:
                    labels = {"in_a": "dòng định mức", "poles": "số cực", "icu_ka": "khả năng cắt"}
                    needed = [labels[k] for k in missing]
                    issue(panel, tag, "Thiếu thông số đóng cắt", "Chưa đọc được: " + ", ".join(needed),
                          recommendation="Đọc lại nhãn trên bản vẽ hoặc bổ sung thông số chỉ định trước khi chọn mã.", required_information=needed)
            upstream = str(d.get("upstream_device") or "").strip()
            # Descriptive supply/busbar references are not missing component tags.
            upstream_normal = unicodedata.normalize('NFD', upstream.lower())
            upstream_normal = ''.join(c for c in upstream_normal if not unicodedata.combining(c)).replace('đ', 'd')
            descriptive_source = any(word in upstream_normal for word in ('thanh cai', 'busbar', 'nguon tong', 'nguon cap', 'tu dien tang', 'ngoai tu'))
            matched_tag = any(re.search(r'(?<!\w)' + re.escape(t) + r'(?!\w)', upstream, re.I) for t in tags)
            if upstream and not matched_tag and not descriptive_source:
                issue(panel, tag, "Chưa tìm thấy thiết bị cấp nguồn", f"Nguồn '{d['upstream_device']}' chưa có trong cùng tủ; kiểm tra tham chiếu ngoài tủ hoặc thiết bị bị sót.")
            if cat == "CONTACTOR" and re.search(r"động cơ|motor|bơm|máy khuấy|máy thổi", " ".join(str(d.get(k) or '') for k in ('connected_load','notes','electrical_function')), re.I):
                # Require an actual connection, not a relay somewhere in the cabinet.
                connected = [x for x in members if x.get("upstream_device") == d.get("tag") or x.get("tag") == d.get("upstream_device")]
                if not any(str(x.get("category") or "").upper() in {"OVERLOAD", "THERMAL_RELAY", "MPCB", "MOTOR_PROTECTION"} for x in connected):
                    issue(panel, tag, "Kiểm tra bảo vệ quá tải của cụm contactor", "Chưa có bằng chứng về bảo vệ quá tải liên kết với cụm. Kiểm tra sơ đồ động lực/điều khiển trước khi đề xuất bổ sung.")
            if not d.get("source_filename"):
                issue(panel, tag, "Thiếu tham chiếu nguồn", "Chưa truy được tệp gốc của thiết bị; yêu cầu nhập bằng văn bản cần xác nhận riêng.")
    return dict(status="needs_review", issues=issues, clusters=clusters,
                automatically_added_devices=0, release_ready=False)


def technical_audit(devices):
    review = review_system(devices)
    from app.services.ai.procurement_review import assembly_requirements
    from app.services.ai.conductor_review import connection_requirements
    from app.services.ai.distribution_review import review_distribution
    panel_devices = defaultdict(list)
    for d in devices:
        raw = d.model_dump() if hasattr(d, 'model_dump') else dict(d)
        panel_devices[str(raw.get('panel_code') or 'CHUA_XAC_DINH')].append(raw)
    def pending(title, detail, recommendation, required_information):
        return dict(title=title, detail=detail, reason=detail, status="ATTENTION", badge="Chưa đủ dữ liệu",
                    certainty="missing_data", severity="info", recommendation=recommendation,
                    required_information=required_information)
    return dict(
        overall_score=None, overall_status="Cần đối soát", summary=f"{len(review['issues'])} điểm cần đối chiếu; chưa xác nhận đủ thiết bị hoặc phù hợp thiết kế.",
        missing_items=review["issues"], cluster_review=review["clusters"], release_ready=False,
        connection_review=[dict(panel_code=panel, connections=connection_requirements(members))
                           for panel,members in panel_devices.items()],
        distribution_review=[dict(panel_code=panel, **review_distribution(members))
                             for panel,members in panel_devices.items()],
        assembly_review=[dict(panel_code=panel, items=assembly_requirements(members),
                             note='Vật tư lắp tủ cần xác nhận theo layout và bộ thiết bị; chưa tự cộng vào tổng. Trụ sứ chỉ khi dùng thanh cái trần.')
                         for panel,members in panel_devices.items()],
        protection_coordination=[pending("Phối hợp bảo vệ", "Chưa đủ dữ liệu kiểm tra chọn lọc và khả năng cắt.",
            "Đối chiếu dòng ngắn mạch tại điểm lắp và bảng phối hợp/đặc tuyến của nhà sản xuất.",
            ["Sơ đồ kết nối", "Dòng ngắn mạch", "Model CB và chỉnh định bảo vệ"])],
        enclosure_environment=[pending("Điều kiện lắp đặt", "Chưa đủ dữ liệu kiểm tra vỏ tủ và tản nhiệt.",
            "Kiểm tra cấp IP, bố trí thiết bị và tính nhiệt theo điều kiện vận hành.",
            ["Môi trường và nhiệt độ", "Cấp IP yêu cầu", "Kích thước và tổn hao thiết bị"])],
        busbar_earthing=[pending("Thanh cái và tiếp địa", "Chưa đủ dữ liệu kiểm tra thanh cái và hệ thống nối đất.",
            "Kiểm tra chịu dòng, chịu ngắn mạch và liên kết PE theo sơ đồ nối đất thực tế.",
            ["Sơ đồ nối đất", "Dòng ngắn mạch", "Vật liệu, tiết diện và cách lắp thanh cái"])],
    )

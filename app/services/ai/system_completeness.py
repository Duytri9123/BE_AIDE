"""Evidence-based review; missing evidence never adds procurement items."""
from collections import defaultdict
import re


def review_system(devices):
    groups = defaultdict(list)
    for raw in devices:
        d = raw.model_dump() if hasattr(raw, "model_dump") else dict(raw)
        groups[str(d.get("panel_code") or "CHUA_XAC_DINH")].append(d)
    issues, clusters = [], []

    def issue(panel, tag, title, detail, *, evidence=None, technical_reference=None):
        issues.append(dict(panel_code=panel, tag=tag, title=title, detail=detail,
                           description=detail, evidence=evidence or [],
                           technical_reference=technical_reference or [],
                           status="ATTENTION", badge="Cần đối chiếu nguồn"))

    for panel, members in groups.items():
        def source_ref(d):
            parts = [str(d.get("source_filename") or "").strip(), str(d.get("tag") or "").strip()]
            if d.get("box_2d"):
                parts.append(f"box_2d={d['box_2d']}")
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
        for d in members:
            tag = str(d.get("tag") or d.get("name") or "Thiết bị")
            text = " ".join(str(d.get(k) or "") for k in ("name", "spec", "electrical_function")).lower()
            cat = str(d.get("category") or "").upper()
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
                    issue(panel, tag, "Thiếu thông số đóng cắt", "Chưa đọc được: " + ", ".join(missing))
            if d.get("upstream_device") and str(d["upstream_device"]) not in tags:
                issue(panel, tag, "Chưa tìm thấy thiết bị cấp nguồn", f"Nguồn '{d['upstream_device']}' chưa có trong cùng tủ; kiểm tra tham chiếu ngoài tủ hoặc thiết bị bị sót.")
            if cat == "CONTACTOR":
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
    def pending(title, detail):
        return dict(title=title, detail=detail, status="ATTENTION", badge="Chưa đủ dữ liệu")
    return dict(
        overall_score=None, overall_status="Cần đối soát", summary=f"{len(review['issues'])} điểm cần đối chiếu; chưa xác nhận đủ thiết bị hoặc phù hợp thiết kế.",
        missing_items=review["issues"], cluster_review=review["clusters"], release_ready=False,
        protection_coordination=[pending("Phối hợp bảo vệ", "Cần sơ đồ kết nối, dòng ngắn mạch tại điểm lắp và đặc tuyến/chỉnh định. So sánh Icu giữa hai CB không chứng minh chọn lọc.")],
        enclosure_environment=[pending("Điều kiện lắp đặt", "Cần môi trường thực tế, cấp IP yêu cầu, kích thước và dữ liệu nhiệt; không suy ra từ dòng tổng.")],
        busbar_earthing=[pending("Thanh cái và tiếp địa", "Cần sơ đồ nối đất, dòng chịu ngắn mạch, điều kiện lắp và tính nhiệt. Số pha không xác định được hệ thống nối đất.")],
    )

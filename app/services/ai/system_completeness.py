"""Evidence-based review; missing evidence never adds procurement items."""
from collections import defaultdict


def review_system(devices):
    groups = defaultdict(list)
    for raw in devices:
        d = raw.model_dump() if hasattr(raw, "model_dump") else dict(raw)
        groups[str(d.get("panel_code") or "CHUA_XAC_DINH")].append(d)
    issues, clusters = [], []

    def issue(panel, tag, title, detail):
        issues.append(dict(panel_code=panel, tag=tag, title=title, detail=detail,
                           description=detail, status="ATTENTION", badge="Cần đối chiếu nguồn"))

    for panel, members in groups.items():
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

"""
PDF Drawing Indexer Service
Dịch vụ phân tích, lập chỉ mục và phân loại các trang bản vẽ cơ điện (M&E) siêu tốc
từ tệp PDF kỹ thuật (AutoCAD/Revit) bằng engine pypdfium2 C.
"""
import re
import os
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
import pypdfium2 as pdfium

logger = logging.getLogger(__name__)


class DrawingCategory:
    SLD = "sld"                    # 1. Sơ đồ nguyên lý tủ điện (Phần Điện Động Lực / Phân Phối)
    LAYOUT = "layout"              # 2. Mặt bằng bố trí vị trí tủ điện (Cấp điện & Chiếu sáng)
    DETAIL_SCHEDULE = "detail_schedule"  # 3. Chi tiết lắp đặt & Thống kê khối lượng tủ điện
    ELV = "elv"                    # 4. Phần Tủ Rack / Tủ Điện nhẹ (ELV)
    DRAWING_LIST = "drawing_list"  # Trang Danh mục / Mục lục bản vẽ
    OTHER = "other"                # Khác (Ghi chú chung, chống sét, kiến trúc, cấp thoát nước, HVAC)


class PdfDrawingIndexerService:
    """
    Trình lập chỉ mục hồ sơ bản vẽ cơ điện tốc độ cao (0.2s - 2s cho 90 trang).
    Nhận diện khung tên, mã hiệu bản vẽ, ký hiệu tủ điện và phân loại thành 4 nhóm chuẩn M&E.
    """

    # Regex nhận dạng mã hiệu bản vẽ M&E chuẩn (ví dụ EL-101, ELV-201, E-101, ME-101...)
    REGEX_PRIMARY_CODE = re.compile(r'\b((?:ELV|EL|ME|M&E|E)[\-_]\d{3}[A-Za-z0-9\-_.]*)\b', re.IGNORECASE)
    REGEX_ANY_CODE = re.compile(r'\b((?:ELV|EL|ME|M&E|E)[\-_]\d+[A-Za-z0-9\-_.]*)\b', re.IGNORECASE)

    # Regex nhận dạng mã tủ điện chuẩn Việt Nam & Quốc tế
    REGEX_PANEL_TAG = re.compile(
        r'\b(?:TĐ|TD)[\-_][A-Z0-9\u00C0-\u01B0\u00C1-\u01B1\u00E0-\u01B2\u00E1-\u01B3\-_/]+'
        r'|\b(?:MSB|MDB|EMDB|ATS|MCC|DB)[\-_]?[A-Z0-9\-_]*\b'
        r'|\b(?:RACK)[\-_]?[A-Z0-9\-_]*\b',
        re.IGNORECASE
    )

    # Từ khóa tìm kiếm ý định người dùng về tủ điện
    PANEL_INTENT_KEYWORDS = [
        "các trang có tủ điện",
        "trang có tủ điện",
        "tìm tủ điện",
        "có bao nhiêu tủ điện",
        "danh sách tủ điện",
        "vị trí tủ điện",
        "sơ đồ tủ điện",
        "trang tủ điện",
        "tủ điện ở đâu",
        "bản vẽ tủ điện",
        "tìm các trang tủ"
    ]

    @classmethod
    def detect_panel_query_intent(cls, prompt: Optional[str]) -> bool:
        """Kiểm tra xem câu lệnh của người dùng có phải là yêu cầu tra cứu/định vị tủ điện không."""
        if not prompt:
            return False
        p_lower = prompt.lower()

        # Nếu là câu lệnh thêm thiết bị hoặc thiết kế tủ mới, không coi là tra cứu trang
        if any(kw in p_lower for kw in ["thêm", "them", "thiết kế tủ", "thiet ke tu", "tạo tủ", "tao tu", "bổ sung", "bo sung"]):
            return False

        # 1. Trùng khớp trực tiếp cụm từ khóa
        if any(kw in p_lower for kw in cls.PANEL_INTENT_KEYWORDS):
            return True

        # 2. Kết hợp ngữ nghĩa: có nhắc đến tủ điện và các từ để hỏi về trang / vị trí / danh mục
        has_panel_word = any(w in p_lower for w in ["tủ điện", "tu dien", "tủ", "tu"])
        has_location_word = any(w in p_lower for w in [
            "trang", "ở đâu", "o dau", "nằm ở", "nam o", "vị trí", "vi tri", 
            "danh sách", "danh sach", "liệt kê", "liet ke", "tìm", "tim", "nào", "nao"
        ])

        return has_panel_word and has_location_word

    @classmethod
    def index_pdf(
        cls,
        file_path: str,
        doc: Optional[pdfium.PdfDocument] = None
    ) -> Dict[str, Any]:
        """
        Quét nhanh toàn bộ các trang PDF và phân tích cấu trúc M&E.
        Trả về metadata, danh sách trang theo nhóm và bảng chỉ mục hoàn chỉnh.
        """
        should_close_doc = False
        if doc is None:
            if not os.path.exists(file_path):
                return {
                    "total_pages": 0,
                    "has_text_layer": False,
                    "pages": [],
                    "categories": {},
                    "sld_pages": [],
                    "all_panel_pages": [],
                    "report_markdown": "File không tồn tại."
                }
            doc = pdfium.PdfDocument(file_path)
            should_close_doc = True

        try:
            total_pages = len(doc)
            pages_data: List[Dict[str, Any]] = []
            has_text_layer = False
            total_text_chars = 0

            # 1. Trích xuất text và phân tích thô từng trang
            for idx in range(total_pages):
                page_num = idx + 1
                try:
                    page = doc[idx]
                    tp = page.get_textpage()
                    raw_text = tp.get_text_range() or ""
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num}: {e}")
                    raw_text = ""

                raw_text_clean = raw_text.strip()
                if len(raw_text_clean) > 20:
                    has_text_layer = True
                    total_text_chars += len(raw_text_clean)

                lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
                upper_text = raw_text.upper()

                # Tìm mã hiệu bản vẽ chuẩn 3 số (EL-101, ELV-201...)
                primary_codes = cls.REGEX_PRIMARY_CODE.findall(raw_text)
                all_codes = cls.REGEX_ANY_CODE.findall(raw_text)

                clean_primary_codes = []
                for sc in primary_codes:
                    sc_clean = sc.upper().strip("._- ")
                    if sc_clean and sc_clean not in clean_primary_codes:
                        clean_primary_codes.append(sc_clean)

                # Mã bản vẽ chính: lấy mã 3 số cuối cùng trên trang (thường ở khung tên góc dưới phải)
                primary_code = clean_primary_codes[-1] if clean_primary_codes else ""
                if not primary_code and all_codes:
                    primary_code = all_codes[-1].upper().strip("._- ")

                # Tìm các mã tủ điện xuất hiện trên trang
                found_tags = set()
                for match in cls.REGEX_PANEL_TAG.findall(raw_text):
                    tag_clean = match.upper().strip("._- ")
                    # Lọc bớt các từ gây nhiễu
                    if len(tag_clean) >= 3 and tag_clean not in {
                        "THE", "AND", "FOR", "CẤP", "ĐIỆN", "TIÊU", "CHUẨN", "DỰNG", "HÌNH", "BẢN"
                    }:
                        found_tags.add(tag_clean)

                is_toc = len(clean_primary_codes) >= 4 or any(
                    kw in upper_text for kw in ["MỤC LỤC", "DANH MỤC BẢN VẼ", "BẢNG KÊ BẢN VẼ", "DANH SÁCH BẢN VẼ", "DRAWING LIST"]
                )

                pages_data.append({
                    "page_idx": idx,
                    "page_num": page_num,
                    "raw_text": raw_text,
                    "upper_text": upper_text,
                    "lines": lines,
                    "primary_codes": clean_primary_codes,
                    "primary_code": primary_code if not is_toc else "",
                    "panel_tags": sorted(list(found_tags)),
                    "is_toc": is_toc,
                    "title": "",
                    "category": DrawingCategory.DRAWING_LIST if is_toc else DrawingCategory.OTHER,
                    "category_reason": ""
                })

            # Nếu PDF không có text layer (file scan ảnh thuần túy), trả về để kích hoạt fallback
            if not has_text_layer or total_text_chars < 100:
                return {
                    "total_pages": total_pages,
                    "has_text_layer": False,
                    "pages": pages_data,
                    "categories": {c: [] for c in [DrawingCategory.SLD, DrawingCategory.LAYOUT, DrawingCategory.DETAIL_SCHEDULE, DrawingCategory.ELV, DrawingCategory.OTHER]},
                    "sld_pages": [],
                    "all_panel_pages": [],
                    "report_markdown": "Tài liệu PDF dạng quét ảnh (không có text layer); cần dùng AI Vision trực tiếp."
                }

            # 2. Quét trang Mục Lục Bản Vẽ để ánh xạ Tiêu Đề chuẩn cho các bản vẽ
            sheet_title_map: Dict[str, str] = {}
            for p in pages_data:
                if p["is_toc"]:
                    for line in p["lines"]:
                        sc_match = cls.REGEX_PRIMARY_CODE.search(line) or cls.REGEX_ANY_CODE.search(line)
                        if sc_match:
                            code = sc_match.group(1).upper()
                            title_part = line.replace(sc_match.group(0), "").strip(" -:.\t0123456789")
                            if len(title_part) >= 4 and not title_part.isdigit():
                                sheet_title_map[code] = title_part

            # 3. Phân loại Category và Tiêu đề từng trang
            for p in pages_data:
                if p["is_toc"]:
                    p["title"] = "Danh mục / Mục lục bản vẽ"
                    p["category"] = DrawingCategory.DRAWING_LIST
                    p["category_reason"] = "Bảng kê danh mục bản vẽ hồ sơ"
                    continue

                u = p["upper_text"]
                code = p["primary_code"]

                # Xác định Tiêu đề (Drawing Title)
                title = sheet_title_map.get(code, "")
                if not title:
                    for line in p["lines"]:
                        line_u = line.upper()
                        if any(kw in line_u for kw in [
                            "SƠ ĐỒ NGUYÊN LÝ", "MẶT BẰNG", "CHI TIẾT LẮP ĐẶT", "BẢNG THỐNG KÊ", 
                            "THỐNG KÊ KHỐI LƯỢNG", "KÝ HIỆU VÀ GHI CHÚ", "SƠ ĐỒ CẤP ĐIỆN", "HỆ THỐNG ĐIỆN NHẸ",
                            "HỆ THỐNG CAMERA", "HỆ THỐNG THÔNG TIN"
                        ]):
                            title = line.strip(" -:.\t")
                            break
                if not title and p["lines"]:
                    for line in p["lines"]:
                        if 8 <= len(line) <= 60 and not re.search(r'^\d+$', line):
                            title = line
                            break
                if not title:
                    title = f"Bản vẽ {code}" if code else f"Trang {p['page_num']}"
                p["title"] = title

                # Nhận diện các phân hệ không thuộc điện (Cấp thoát nước, HVAC) để loại trừ
                is_non_electrical = any(kw in u for kw in [
                    "CẤP THOÁT NƯỚC", "CẤP NƯỚC", "THOÁT NƯỚC", "NƯỚC MƯA", "NƯỚC THẢI",
                    "ĐIỀU HÒA THÔNG GIÓ", "ĐIỀU HOÀ KHÔNG KHÍ", "ỐNG GAS", "THÔNG GIÓ",
                    "NƯỚC NGƯNG", "GAS -"
                ]) and not any(kw in u for kw in ["CẤP ĐIỆN", "TỦ ĐIỆN", "CHIẾU SÁNG", "EL-", "ELV-"])

                has_panel_tags = len(p["panel_tags"]) > 0
                has_rack_tag = any("RACK" in t for t in p["panel_tags"])

                # NHÓM 4: Tủ Rack / Tủ Điện nhẹ (ELV)
                if (
                    code.startswith("ELV") or 
                    "ELV-" in u or 
                    ("ĐIỆN NHẸ" in u and "MẶT BẰNG" in u) or
                    "HỆ THỐNG THÔNG TIN" in u or
                    "HỆ THỐNG CAMERA" in u or
                    "HỆ THỐNG ÂM THANH" in u or
                    (has_rack_tag and not code.startswith("EL-"))
                ) and not is_non_electrical:
                    p["category"] = DrawingCategory.ELV
                    p["category_reason"] = "Bản vẽ hệ thống điện nhẹ / Tủ Rack ELV"

                # NHÓM 1: Sơ đồ nguyên lý tủ điện (Phần Điện - SLD)
                elif (
                    (code.startswith(("EL-1", "E-1")) and not code.startswith("EL-1.")) or
                    (
                        any(kw in u for kw in ["SƠ ĐỒ NGUYÊN LÝ", "SLD", "SƠ ĐỒ CẤP ĐIỆN", "SƠ ĐỒ TỦ", "TỦ PHÂN PHỐI"]) and
                        any(kw in u for kw in ["CẤP ĐIỆN", "TỦ ĐIỆN", "HẠ THẾ", "TĐ-", "MSB", "ATS"]) and
                        not is_non_electrical
                    )
                ) and not any(kw in u for kw in ["MẶT BẰNG", "CHI TIẾT LẮP ĐẶT"]):
                    p["category"] = DrawingCategory.SLD
                    p["category_reason"] = "Sơ đồ nguyên lý một sợi (SLD) thể hiện thiết bị tủ điện"

                # NHÓM 3: Chi tiết lắp đặt & Thống kê khối lượng tủ điện
                elif (
                    (code.startswith(("EL-5", "EL-6", "E-5", "E-6"))) or
                    (
                        any(kw in u for kw in ["CHI TIẾT LẮP ĐẶT", "BẢNG THỐNG KÊ", "THỐNG KÊ KHỐI LƯỢNG", "SCHEDULE"]) and
                        any(kw in u for kw in ["TỦ ĐIỆN", "CẤP ĐIỆN", "THIẾT BỊ ĐIỆN", "HẠ THẾ", "EL-"]) and
                        not is_non_electrical
                    )
                ):
                    p["category"] = DrawingCategory.DETAIL_SCHEDULE
                    p["category_reason"] = "Chi tiết lắp đặt hoặc Bảng thống kê khối lượng tủ điện"

                # NHÓM 2: Mặt bằng bố trí vị trí tủ điện (Cấp điện & Chiếu sáng)
                elif (
                    (code.startswith(("EL-2", "EL-3", "E-2", "E-3"))) or
                    (
                        any(kw in u for kw in ["MẶT BẰNG CẤP ĐIỆN", "MẶT BẰNG CHIẾU SÁNG", "MẶT BẰNG BỐ TRÍ"]) and
                        not is_non_electrical
                    ) or
                    (has_panel_tags and "MẶT BẰNG" in u and not is_non_electrical)
                ):
                    p["category"] = DrawingCategory.LAYOUT
                    p["category_reason"] = "Mặt bằng cấp điện/chiếu sáng thể hiện vị trí lắp đặt tủ"

                else:
                    p["category"] = DrawingCategory.OTHER
                    p["category_reason"] = "Bản vẽ phụ trợ, ghi chú, cấp thoát nước hoặc HVAC"

            # Phân nhóm danh mục
            categories_map: Dict[str, List[Dict[str, Any]]] = {
                DrawingCategory.SLD: [],
                DrawingCategory.LAYOUT: [],
                DrawingCategory.DETAIL_SCHEDULE: [],
                DrawingCategory.ELV: [],
                DrawingCategory.DRAWING_LIST: [],
                DrawingCategory.OTHER: []
            }
            for p in pages_data:
                categories_map[p["category"]].append(p)

            # Danh sách trang SLD ưu tiên bóc tách BOM thiết bị
            sld_page_numbers = [p["page_num"] for p in categories_map[DrawingCategory.SLD]]

            # Danh sách tất cả các trang có liên quan đến tủ điện
            panel_pages = []
            for p in pages_data:
                if p["category"] in [DrawingCategory.SLD, DrawingCategory.DETAIL_SCHEDULE, DrawingCategory.ELV]:
                    panel_pages.append(p["page_num"])
                elif p["category"] == DrawingCategory.LAYOUT and (p["panel_tags"] or "CẤP ĐIỆN" in p["upper_text"]):
                    panel_pages.append(p["page_num"])
            panel_pages = sorted(list(set(panel_pages)))

            result = {
                "total_pages": total_pages,
                "has_text_layer": True,
                "pages": pages_data,
                "categories": categories_map,
                "sld_pages": sld_page_numbers,
                "all_panel_pages": panel_pages,
                "report_markdown": cls.format_mne_report(categories_map, total_pages)
            }
            return result

        finally:
            if should_close_doc and doc:
                try:
                    doc.close()
                except Exception:
                    pass

    @classmethod
    def format_mne_report(
        cls,
        categories: Dict[str, List[Dict[str, Any]]],
        total_pages: int
    ) -> str:
        """
        Tạo báo cáo chi tiết các trang có tủ điện theo đúng cấu trúc 4 nhóm chuẩn M&E.
        """
        lines = [
            f"Dưới đây là danh sách các trang/bản vẽ có thể hiện hoặc chi tiết về tủ điện (tủ điện động lực, tủ phân phối, tủ điều khiển và tủ rack điện nhẹ) trong bộ hồ sơ ({total_pages} trang):\n"
        ]

        # 1. Sơ đồ nguyên lý tủ điện (Phần Điện)
        sld_list = categories.get(DrawingCategory.SLD, [])
        lines.append("### 1. Bản vẽ Sơ đồ nguyên lý tủ điện (Phần Điện)")
        if sld_list:
            for p in sld_list:
                code_str = f" ({p['primary_code']})" if p['primary_code'] else ""
                panel_desc = f" – Thể hiện các tủ: {', '.join(p['panel_tags'])}" if p['panel_tags'] else ""
                lines.append(f"- **Trang {p['page_num']}{code_str}**: {p['title']}{panel_desc}.")
        else:
            lines.append("- *Không phát hiện sơ đồ nguyên lý riêng biệt.*")
        lines.append("")

        # 2. Bản vẽ Mặt bằng bố trí vị trí tủ điện (Cấp điện & Chiếu sáng)
        layout_list = categories.get(DrawingCategory.LAYOUT, [])
        lines.append("### 2. Bản vẽ Mặt bằng bố trí vị trí tủ điện (Cấp điện & Chiếu sáng)")
        if layout_list:
            for p in layout_list:
                code_str = f" ({p['primary_code']})" if p['primary_code'] else ""
                panel_desc = f" (vị trí {', '.join(p['panel_tags'])})" if p['panel_tags'] else ""
                lines.append(f"- **Trang {p['page_num']}{code_str}**: {p['title']}{panel_desc}.")
        else:
            lines.append("- *Không có mặt bằng bố trí tủ điện.*")
        lines.append("")

        # 3. Chi tiết lắp đặt & Thống kê khối lượng tủ điện
        detail_list = categories.get(DrawingCategory.DETAIL_SCHEDULE, [])
        lines.append("### 3. Chi tiết lắp đặt & Thống kê khối lượng tủ điện")
        if detail_list:
            for p in detail_list:
                code_str = f" ({p['primary_code']})" if p['primary_code'] else ""
                lines.append(f"- **Trang {p['page_num']}{code_str}**: {p['title']}.")
        else:
            lines.append("- *Không có bảng chi tiết lắp đặt hoặc thống kê.*")
        lines.append("")

        # 4. Phần Tủ Rack / Tủ Điện nhẹ (ELV)
        elv_list = categories.get(DrawingCategory.ELV, [])
        lines.append("### 4. Phần Tủ Rack / Tủ Điện nhẹ (ELV)")
        if elv_list:
            for p in elv_list:
                code_str = f" ({p['primary_code']})" if p['primary_code'] else ""
                panel_desc = f" – Thể hiện {', '.join(p['panel_tags'])}" if p['panel_tags'] else ""
                lines.append(f"- **Trang {p['page_num']}{code_str}**: {p['title']}{panel_desc}.")
        else:
            lines.append("- *Không có bản vẽ tủ rack điện nhẹ riêng biệt.*")

        return "\n".join(lines)

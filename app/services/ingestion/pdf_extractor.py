import io
import base64
from PIL import Image
import pdfplumber
import re
import logging
from typing import List, Dict, Any, Optional, Tuple

from app.core.exceptions import PDFParsingError
from app.core.device_patterns import DevicePatterns, DeviceMatch
from app.core.config import settings

logger = logging.getLogger(__name__)


class PdfExtractorService:
    @staticmethod
    def extract_tables(file_path: str) -> list[dict]:
        """Trích xuất tất cả các bảng từ PDF."""
        try:
            tables = []
            with pdfplumber.open(file_path) as pdf:
                logger.info(f"Extracting tables from PDF: {file_path} ({len(pdf.pages)} pages)")
                for page_num, page in enumerate(pdf.pages):
                    extracted = page.extract_table()
                    if extracted:
                        tables.append({
                            "page": page_num + 1,
                            "data": extracted
                        })
            logger.info(f"Extracted {len(tables)} tables from PDF")
            return tables
        except FileNotFoundError:
            raise PDFParsingError(
                f"File PDF không tồn tại: {file_path}",
                {"path": file_path}
            )
        except PermissionError:
            raise PDFParsingError(
                f"Không có quyền đọc file PDF: {file_path}",
                {"path": file_path}
            )
        except Exception as e:
            logger.error(f"Failed to extract tables from PDF: {str(e)}", exc_info=True)
            raise PDFParsingError(
                f"Lỗi khi trích xuất bảng từ PDF: {str(e)}",
                {"path": file_path, "error": str(e)}
            )

    @staticmethod
    def extract_text(file_path: str) -> str:
        """Trích xuất toàn bộ text từ PDF."""
        try:
            text = ""
            with pdfplumber.open(file_path) as pdf:
                logger.info(f"Extracting text from PDF: {file_path}")
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            logger.info(f"Extracted {len(text)} characters from PDF")
            return text
        except FileNotFoundError:
            raise PDFParsingError(
                f"File PDF không tồn tại: {file_path}",
                {"path": file_path}
            )
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {str(e)}", exc_info=True)
            raise PDFParsingError(
                f"Lỗi khi trích xuất text từ PDF: {str(e)}",
                {"path": file_path, "error": str(e)}
            )

    @staticmethod
    def extract_schedule(file_path: str) -> list[dict]:
        """
        Phân tích Panel Schedule (tủ phân phối) từ text PDF
        Sử dụng DevicePatterns với regex linh hoạt
        """
        try:
            text = PdfExtractorService.extract_text(file_path)
            
            # Use advanced patterns
            devices = DevicePatterns.extract_from_panel_schedule(text)
            
            # Also try general extraction if schedule format doesn't match
            if len(devices) == 0:
                devices = DevicePatterns.extract_all_devices(text)
            
            # Convert to dict format
            schedules = []
            for dev in devices:
                schedules.append({
                    "type": dev.category,
                    "poles": f"{dev.poles}P" if dev.poles else "",
                    "in_a": dev.in_a,
                    "icu_ka": dev.icu_ka,
                    "brand": dev.brand,
                    "confidence": dev.confidence
                })
            
            logger.info(f"Extracted {len(schedules)} devices from PDF schedule")
            return schedules
            
        except PDFParsingError:
            raise
        except Exception as e:
            logger.error(f"Failed to extract schedule: {str(e)}", exc_info=True)
            raise PDFParsingError(
                f"Lỗi khi phân tích panel schedule: {str(e)}",
                {"path": file_path, "error": str(e)}
            )
    
    @staticmethod
    def extract_devices_from_text_content(file_path: str) -> List[DeviceMatch]:
        """
        Extract devices từ toàn bộ text content của PDF
        Sử dụng advanced patterns, support nhiều format
        
        Returns:
            List of DeviceMatch objects
        """
        try:
            text = PdfExtractorService.extract_text(file_path)
            devices = DevicePatterns.extract_all_devices(text)
            
            logger.info(f"Extracted {len(devices)} devices from PDF text content")
            return devices
            
        except PDFParsingError:
            raise
        except Exception as e:
            logger.error(f"Failed to extract devices from PDF: {str(e)}", exc_info=True)
            raise PDFParsingError(
                f"Lỗi khi trích xuất thiết bị từ PDF: {str(e)}",
                {"path": file_path, "error": str(e)}
            )

    @staticmethod
    def extract_multi_panel_schedules(file_path: str) -> List[Dict[str, Any]]:
        """
        Bóc tách chi tiết nhiều tủ điện và nhiều loại sơ đồ nguyên lý 1 sợi (SLD) từ file PDF.
        Nhận diện chính xác từng tủ riêng biệt, vị trí trang & mã bản vẽ, kích thước định hướng,
        ghi chú kỹ thuật, thiết bị đầu vào Incomer, đo lường & các lộ nhánh ra.
        Không gán ép thương hiệu khi bản vẽ chỉ ghi thông số kỹ thuật thuần túy.
        """
        try:
            results: List[Dict[str, Any]] = []
            with pdfplumber.open(file_path) as pdf:
                logger.info(f"Analyzing multi-panel schedules from PDF: {file_path} ({len(pdf.pages)} pages)")
                
                for page_idx, page in enumerate(pdf.pages):
                    page_num = page_idx + 1
                    full_text = page.extract_text() or ""
                    
                    # Bỏ qua trang bìa, mục lục chung chỉ khi không chứa sơ đồ hoặc thiết bị điện
                    is_pure_toc = ("DANH MỤC BẢN VẼ" in full_text.upper() or "MỤC LỤC" in full_text.upper()) and not any(k in full_text.upper() for k in ["MCCB", "MCB", "ACB", "SƠ ĐỒ", "DIAGRAM", "SLD"])
                    if is_pure_toc:
                        continue

                    # Kiểm tra trang có chứa sơ đồ nguyên lý hoặc ký hiệu thiết bị điện
                    has_electrical_content = any(k in full_text.upper() for k in [
                        "MCCB", "MCB", "ACB", "RCBO", "CONTACTOR", "SƠ ĐỒ", "TỦ ĐIỆN", "SLD",
                        "SINGLE LINE", "DIAGRAM", "THANH CÁI", "FEEDER", "INCOMER", "MDB", "MSB", "DB", "LP", "MCC", "CC TĐ", "CC TS"
                    ])
                    if not has_electrical_content:
                        continue

                    # Lazy rendering ảnh trang PDF phục vụ trích xuất ảnh dẫn chứng trực quan (Visual Evidence Thumbnail)
                    page_img = None
                    sx = 1.0
                    sy = 1.0

                    def get_page_img():
                        nonlocal page_img, sx, sy
                        if page_img is None:
                            try:
                                page_img = page.to_image(resolution=280).original
                                iw, ih = page_img.size
                                sx = iw / float(page.width)
                                sy = ih / float(page.height)
                            except Exception as img_err:
                                logger.warning(f"Could not render page {page_num} image: {img_err}")
                        return page_img

                    def make_thumbnail(bx0, by0, bx1, by1, min_w=100.0, min_h=80.0):
                        """Crop vùng chỉ định từ trang PDF cận cảnh, rõ nét từng chi tiết ký hiệu và chữ số."""
                        img = get_page_img()
                        if img is None:
                            return None, None

                        # Padding và mở rộng khung để không bị cắt chữ hoặc que dọc méo
                        rx0 = float(bx0)
                        ry0 = float(by0)
                        rx1 = float(bx1)
                        ry1 = float(by1)

                        cur_w = rx1 - rx0
                        cur_h = ry1 - ry0

                        if cur_w < min_w:
                            pad_w = (min_w - cur_w) / 2.0
                            rx0 = max(0.0, rx0 - pad_w)
                            rx1 = min(float(page.width), rx1 + pad_w)

                        if cur_h < min_h:
                            pad_h = (min_h - cur_h) / 2.0
                            ry0 = max(0.0, ry0 - pad_h)
                            ry1 = min(float(page.height), ry1 + pad_h)

                        # Padding an toàn
                        rx0 = max(0.0, rx0 - 10.0)
                        ry0 = max(0.0, ry0 - 10.0)
                        rx1 = min(float(page.width), rx1 + 10.0)
                        ry1 = min(float(page.height), ry1 + 10.0)

                        px0 = max(0, int(rx0 * sx))
                        py0 = max(0, int(ry0 * sy))
                        px1 = min(img.width, int(rx1 * sx))
                        py1 = min(img.height, int(ry1 * sy))
                        if px1 <= px0 or py1 <= py0:
                            return None, None

                        try:
                            crop = img.crop((px0, py0, px1, py1))
                            if crop.mode in ("RGBA", "LA", "P"):
                                crop = crop.convert("RGB")
                            crop.thumbnail((1600, 1200), Image.Resampling.LANCZOS)
                            buf = io.BytesIO()
                            crop.save(buf, format="JPEG", quality=95)
                            b64 = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"
                            box_2d = [
                                int(ry0 / float(page.height) * 1000),
                                int(rx0 / float(page.width) * 1000),
                                int(ry1 / float(page.height) * 1000),
                                int(rx1 / float(page.width) * 1000)
                            ]
                            return b64, box_2d
                        except Exception as crop_err:
                            logger.warning(f"Thumbnail crop error on page {page_num}: {crop_err}")
                            return None, None

                    def make_panel_thumbnail(rx0, rx1):
                        """Crop toàn bộ chiều ngang vùng tủ, từ đỉnh sơ đồ đến chân sơ đồ tủ."""
                        img = get_page_img()
                        if img is None:
                            return None, None
                        px0 = max(0, int(rx0 * sx))
                        py0 = max(0, int(0.03 * img.height))
                        px1 = min(img.width, int(rx1 * sx))
                        py1 = min(img.height, int(0.90 * img.height))
                        if px1 <= px0 or py1 <= py0:
                            return None, None
                        try:
                            crop = img.crop((px0, py0, px1, py1))
                            if crop.mode in ("RGBA", "LA", "P"):
                                crop = crop.convert("RGB")
                            crop.thumbnail((1400, 1100), Image.Resampling.LANCZOS)
                            buf = io.BytesIO()
                            crop.save(buf, format="JPEG", quality=95)
                            b64 = f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"
                            box_2d = [
                                30,
                                int(rx0 / float(page.width) * 1000),
                                900,
                                int(rx1 / float(page.width) * 1000)
                            ]
                            return b64, box_2d
                        except Exception as crop_err:
                            logger.warning(f"Panel thumbnail crop error on page {page_num}: {crop_err}")
                            return None, None

                    # 1. Trích xuất mã hiệu bản vẽ & tên bản vẽ
                    m_dwg = re.search(r'([ĐD]-\d+\.\d+[A-Z]?)', full_text)
                    dwg_code = m_dwg.group(1) if m_dwg else f"Trang {page_num}"
                    
                    m_dwg_name = re.search(r'tên bản vẽ:\s*([^\n\r]+)', full_text, re.IGNORECASE)
                    dwg_name = m_dwg_name.group(1).strip() if m_dwg_name else ""

                    words = page.extract_words()
                    
                    # 2. Phát hiện các phân vùng tủ điện thực tế trên cùng 1 trang
                    # Chỉ chia nhiều tủ khi có bằng chứng kỹ thuật rõ ràng: Nhiều Aptomat tổng Incomer hoặc nhiều mã tủ độc lập
                    top_incomers = [w for w in words if w['text'] in ['ACB', 'MCCB'] and w['top'] < 165]
                    panel_codes_found = re.findall(r'(?:CC\s+)?([T][ĐDS][\.\-_A-Za-z0-9]+|\b(?:MSB|MDB|DB|LP|MCC)[\-_0-9A-Za-z]+)', full_text)
                    unique_codes = list(dict.fromkeys([c.replace("CC ", "").strip() for c in panel_codes_found if len(c.strip()) >= 3 and not c.strip().endswith("mm")]))

                    dividers: List[float] = []
                    # Chỉ áp dụng chia cột nếu thực sự có từ 2 Incomer hoặc 2 mã tủ độc lập trở lên trên cùng 1 trang
                    if len(top_incomers) > 1 or len(unique_codes) > 1:
                        dev_words = [w for w in words if w['text'] in ['MCCB', 'MCB', 'RCBO'] and 160 < w['top'] < 240]
                        xs = sorted(set(round(w['x0'], 1) for w in dev_words))
                        for i in range(len(xs) - 1):
                            gap = xs[i+1] - xs[i]
                            # Khoảng cách giữa 2 tủ tách biệt rõ ràng thường > 80mm
                            if gap > 80.0:
                                dividers.append((xs[i] + xs[i+1]) / 2.0)

                    panel_regions: List[tuple[float, float]] = []
                    x_start = 0.0
                    for div in dividers:
                        panel_regions.append((x_start, div))
                        x_start = div
                    panel_regions.append((x_start, float(page.width)))

                    # 3. Phân tích từng phân vùng tủ điện
                    for region_idx, (x0, x1) in enumerate(panel_regions):
                        crop = page.crop((x0, 0, x1, page.height))
                        c_text = crop.extract_text() or ""
                        c_words = crop.extract_words()

                        # Xác định Mã tủ & Tên tủ
                        # Tìm mã tủ chuẩn (ví dụ: TĐ.TSXĐ-01- 630A, TĐ-01, MSB-01, DB-01)
                        m_code = re.search(r'(?:CC\s+)?([T][ĐDS][\.\-_A-Za-z0-9]+(?:\s*-\s*\d+[A-Za-z]*)?)', c_text)
                        panel_code = m_code.group(1).strip() if m_code else ""
                        if not panel_code or len(panel_code) < 3 or panel_code.endswith("mm"):
                            m_code2 = re.search(r'\b(MSB|MDB|DB|LP|MCC)[\-_0-9A-Za-z]+', c_text)
                            panel_code = m_code2.group(0).strip() if m_code2 else (unique_codes[region_idx] if region_idx < len(unique_codes) else f"TĐ-{page_num}")

                        # Trích xuất tên tủ: ưu tiên tiêu đề kỹ thuật, loại bỏ các cụm từ mô tả lắp đặt
                        m_pname = re.search(r'(?:SƠ ĐỒ\s+)?(TỦ ĐIỆN[^\n\r]+)', c_text)
                        raw_panel_name = m_pname.group(1).strip() if m_pname else ""
                        if not raw_panel_name or "LOẠI LẮP" in raw_panel_name.upper() or "THỰC TẾ" in raw_panel_name.upper():
                            # Tìm lại trên toàn trang hoặc tạo tên có ý nghĩa
                            m_pname_full = re.search(r'(?:SƠ ĐỒ\s+)?(TỦ ĐIỆN[^\n\r]+)', full_text)
                            if m_pname_full and "LOẠI LẮP" not in m_pname_full.group(1).upper():
                                raw_panel_name = m_pname_full.group(1).strip()
                            else:
                                raw_panel_name = f"Tủ điện phân phối {panel_code}"
                        panel_name = raw_panel_name

                        # Kích thước định hướng thiết kế
                        m_dim = re.search(r'\((\d+)x(\d+)x(\d+)x([\d\.]+)\)mm', c_text)
                        dim_str = m_dim.group(0) if m_dim else ""
                        dim_h = int(m_dim.group(1)) if m_dim else 1200
                        dim_w = int(m_dim.group(2)) if m_dim else 700
                        dim_d = int(m_dim.group(3)) if m_dim else 250
                        dim_t = float(m_dim.group(4)) if m_dim else settings.ENCLOSURE_DEFAULT_THICKNESS

                        # Ghi chú kỹ thuật từ bản vẽ
                        panel_notes: List[str] = []
                        notes_source = c_text if ("VÁCH CÁCH ĐIỆN" in c_text.upper() or "NỐI ĐẤT" in c_text.upper()) else full_text
                        if "VÁCH CÁCH ĐIỆN" in notes_source.upper() or "MICA" in notes_source.upper():
                            panel_notes.append("Giữa các cực pha của Aptomat phải có vách cách điện bằng mica hoặc cao su chống giật.")
                        if "NỐI ĐẤT" in notes_source.upper():
                            panel_notes.append("Tủ điện phải được nối đất an toàn theo quy định.")
                        if "ĐỊNH HƯỚNG" in notes_source.upper() or "THAM KHẢO" in notes_source.upper():
                            panel_notes.append("Kích thước vỏ tủ mang tính chất định hướng/tham khảo, có thể điều chỉnh phù hợp thiết bị thực tế.")

                        panel_devices: List[Dict[str, Any]] = []

                        # A. Thiết bị Đầu vào (Incomer)
                        top_breakers = [w for w in c_words if w['top'] < 175 and w['text'] in ['ACB', 'MCCB', 'MCB']]
                        inc_cat = "ACB" if "ACB" in c_text.upper() else "MCCB"
                        inc_poles = 4 if "4P" in c_text.upper() else 3
                        inc_in = 63.0
                        inc_icu = None

                        # Tìm dòng định mức In của lộ tổng (loại bỏ 2A của cầu chì đèn báo)
                        m_incomer_text = re.search(r'(?:ACB|MCCB)[\s\S]{0,50}?(?:([1-4]P)\s+)?(\d{2,4})A', c_text, re.IGNORECASE)
                        if not m_incomer_text:
                            m_incomer_text = re.search(r'(?:([1-4]P)[\s\-_]+)?(\d{2,4})A[\s\S]{0,30}?(?:ACB|MCCB)', c_text, re.IGNORECASE)

                        if m_incomer_text:
                            if m_incomer_text.group(1):
                                inc_poles = int(m_incomer_text.group(1).upper().replace("P", ""))
                            inc_in = float(m_incomer_text.group(2))
                        else:
                            # Tìm dòng Ampe lớn nhất trong 500 ký tự đầu của tủ
                            amp_matches = re.findall(r'\b(\d{2,4})\s*A\b', c_text[:500])
                            amps = [float(a) for a in amp_matches if float(a) >= 32 and float(a) not in [220, 380]]
                            if amps:
                                inc_in = max(amps)

                        m_icu = re.search(r'(\d{1,3})\s*kA', c_text[:500], re.IGNORECASE)
                        if m_icu:
                            inc_icu = float(m_icu.group(1))
                        else:
                            inc_icu = 50.0 if inc_in >= 1000 else (36.0 if inc_in >= 250 else (18.0 if inc_in >= 100 else 6.0))

                        reg_w = x1 - x0
                        panel_img, panel_box = make_panel_thumbnail(x0, x1)

                        # 1. Ảnh dẫn chứng zoom cận cảnh Aptomat tổng Incomer (ACB / MCCB tổng)
                        if top_breakers:
                            bw = top_breakers[0]
                            cx = (bw['x0'] + bw['x1']) / 2.0
                            cy = (bw['top'] + bw['bottom']) / 2.0
                            inc_img, inc_box = make_thumbnail(cx - 75, cy - 70, cx + 75, cy + 85, min_w=150.0, min_h=130.0)
                        else:
                            inc_words = [w for w in c_words if any(k in w['text'].upper() for k in ['ACB', 'MCCB', 'INCOMER', 'TỔNG']) and w['top'] < 220]
                            if inc_words:
                                min_wx = min(w['x0'] for w in inc_words)
                                max_wx = max(w['x1'] for w in inc_words)
                                min_wy = min(w['top'] for w in inc_words)
                                max_wy = max(w['bottom'] for w in inc_words)
                                inc_img, inc_box = make_thumbnail(min_wx - 50, min_wy - 50, max_wx + 50, max_wy + 60, min_w=150.0, min_h=130.0)
                            else:
                                inc_img, inc_box = make_thumbnail(x0 + 10, 40.0, min(x1 - 10, x0 + 160), 220.0, min_w=150.0, min_h=130.0)

                        if not inc_img:
                            inc_img, inc_box = panel_img, panel_box

                        panel_devices.append({
                            "category": inc_cat,
                            "name": f"{inc_cat} {inc_poles}P {int(inc_in)}A {int(inc_icu)}kA (Aptomat tổng Incomer)",
                            "spec": f"{inc_poles}P - {int(inc_in)}A - {int(inc_icu)}kA",
                            "in_a": inc_in,
                            "icu_ka": inc_icu,
                            "poles": inc_poles,
                            "quantity": 1,
                            "brand": "",
                            "part_number": "",
                            "section": "Đầu vào",
                            "location": f"Trang {page_num} - Bản vẽ {dwg_code} (Tủ {panel_code})",
                            "panel_code": panel_code,
                            "panel_name": panel_name,
                            "notes": f"Aptomat tổng cấp nguồn tủ {panel_code}",
                            "confidence": settings.DEFAULT_CONFIDENCE,
                            "evidence_image": inc_img,
                            "panel_evidence_image": panel_img,
                            "box_2d": inc_box,
                            "suggested_brands": []
                        })

                        # B. Thiết bị Đo lường & Giám sát
                        ct_match = re.search(r'(?:3x)?(\d+)\s*A?/5A', c_text)
                        if "PM" in c_text:
                            meter_words = [w for w in c_words if any(k in w['text'].upper() for k in ['PM', 'MFM', 'ĐỒNG HỒ', 'METER', 'KWH']) and w['top'] < 250]
                            if meter_words:
                                mcx = sum((w['x0'] + w['x1']) / 2.0 for w in meter_words) / len(meter_words)
                                mcy = sum((w['top'] + w['bottom']) / 2.0 for w in meter_words) / len(meter_words)
                                m_img, m_box = make_thumbnail(mcx - 65, mcy - 50, mcx + 65, mcy + 60, min_w=130.0, min_h=100.0)
                            else:
                                m_img, m_box = make_thumbnail(x0 + 10, 40.0, min(x1 - 10, x0 + 140), 180.0, min_w=130.0, min_h=100.0)
                            if not m_img:
                                m_img, m_box = panel_img, panel_box

                            panel_devices.append({
                                "category": "METER",
                                "name": "Đồng hồ đa năng kỹ thuật số (đo V, A, Hz, CosPhi, kWh)",
                                "spec": "Màn hình LCD đa chức năng, gắn mặt cánh tủ",
                                "in_a": None,
                                "icu_ka": None,
                                "poles": 3,
                                "quantity": 1,
                                "brand": "",
                                "part_number": "",
                                "section": "Đo lường & Giám sát",
                                "location": f"Trang {page_num} - Bản vẽ {dwg_code} (Tủ {panel_code})",
                                "panel_code": panel_code,
                                "panel_name": panel_name,
                                "notes": "Đo lường tổng hợp dòng, áp và điện năng",
                                "confidence": 0.95,
                                "evidence_image": m_img,
                                "panel_evidence_image": panel_img,
                                "box_2d": m_box,
                                "suggested_brands": []
                            })

                        if ct_match:
                            ct_ratio = ct_match.group(1)
                            ct_words = [w for w in c_words if ('/5A' in w['text'] or 'CT' in w['text'].upper()) and w['top'] < 250]
                            if ct_words:
                                ccx = sum((w['x0'] + w['x1']) / 2.0 for w in ct_words) / len(ct_words)
                                ccy = sum((w['top'] + w['bottom']) / 2.0 for w in ct_words) / len(ct_words)
                                ct_img, ct_box = make_thumbnail(ccx - 65, ccy - 50, ccx + 65, ccy + 55, min_w=130.0, min_h=100.0)
                            else:
                                ct_img, ct_box = make_thumbnail(x0 + 10, 60.0, min(x1 - 10, x0 + 150), 200.0, min_w=130.0, min_h=100.0)
                            if not ct_img:
                                ct_img, ct_box = panel_img, panel_box

                            panel_devices.append({
                                "category": "CT",
                                "name": f"Biến dòng đo lường hạ thế CT {ct_ratio}/5A",
                                "spec": f"Tỷ số {ct_ratio}/5A - Cấp chính xác Class 0.5",
                                "in_a": float(ct_ratio),
                                "icu_ka": None,
                                "poles": 1,
                                "quantity": 3,
                                "brand": "",
                                "part_number": "",
                                "section": "Đo lường & Giám sát",
                                "location": f"Trang {page_num} - Bản vẽ {dwg_code} (Tủ {panel_code})",
                                "panel_code": panel_code,
                                "panel_name": panel_name,
                                "notes": "Bộ 3 quả biến dòng cấp tín hiệu cho đồng hồ PM",
                                "confidence": 0.95,
                                "evidence_image": ct_img,
                                "panel_evidence_image": panel_img,
                                "box_2d": ct_box,
                                "suggested_brands": []
                            })

                        if "R Y B" in c_text or "CHỈ THỊ" in c_text:
                            light_words = [w for w in c_words if any(k in w['text'].upper() for k in ['R', 'S', 'T', 'CHỈ THỊ', 'ĐÈN', 'FUSE', '2A']) and w['top'] < 160]
                            if light_words:
                                lcx = sum((w['x0'] + w['x1']) / 2.0 for w in light_words) / len(light_words)
                                lcy = sum((w['top'] + w['bottom']) / 2.0 for w in light_words) / len(light_words)
                                l_img, l_box = make_thumbnail(lcx - 60, lcy - 40, lcx + 60, lcy + 50, min_w=120.0, min_h=90.0)
                            else:
                                l_img, l_box = make_thumbnail(x0 + 10, 30.0, min(x1 - 10, x0 + 130), 160.0, min_w=120.0, min_h=90.0)
                            if not l_img:
                                l_img, l_box = panel_img, panel_box

                            panel_devices.append({
                                "category": "LIGHT",
                                "name": "Bộ 3 đèn báo pha LED R-S-T kèm cầu chì bảo vệ 2A",
                                "spec": "Phi 22 - 220VAC (Đỏ, Vàng, Xanh) + 3 cầu chì 2A",
                                "in_a": 2.0,
                                "icu_ka": None,
                                "poles": 1,
                                "quantity": 3,
                                "brand": "",
                                "part_number": "",
                                "section": "Đo lường & Giám sát",
                                "location": f"Trang {page_num} - Bản vẽ {dwg_code} (Tủ {panel_code})",
                                "panel_code": panel_code,
                                "panel_name": panel_name,
                                "notes": "Đèn báo nguồn pha trên mặt cánh tủ",
                                "confidence": 0.95,
                                "evidence_image": l_img,
                                "panel_evidence_image": panel_img,
                                "box_2d": l_box,
                                "suggested_brands": []
                            })

                        # C. Thiết bị Điều khiển (nếu có Contactor)
                        if "CONTACTOR" in c_text.upper():
                            cont_words = [w for w in c_words if 'CONTACTOR' in w['text'].upper()]
                            if cont_words:
                                kcx = (cont_words[0]['x0'] + cont_words[0]['x1']) / 2.0
                                kcy = (cont_words[0]['top'] + cont_words[0]['bottom']) / 2.0
                                cnt_img, cnt_box = make_thumbnail(kcx - 65, kcy - 55, kcx + 65, kcy + 60, min_w=130.0, min_h=110.0)
                            else:
                                cnt_img, cnt_box = panel_img, panel_box

                            panel_devices.append({
                                "category": "CONTACTOR",
                                "name": "Contactor điều khiển chiếu sáng 1P 16A",
                                "spec": "1P - 16A - Cuộn hút 220VAC",
                                "in_a": 16.0,
                                "icu_ka": None,
                                "poles": 1,
                                "quantity": 1,
                                "brand": "",
                                "part_number": "",
                                "section": "Điều khiển & Chiếu sáng",
                                "location": f"Trang {page_num} - Bản vẽ {dwg_code} (Tủ {panel_code})",
                                "panel_code": panel_code,
                                "panel_name": panel_name,
                                "notes": "Điều khiển chiếu sáng tự động/bằng tay kèm nút ấn ON/OFF trên cánh tủ",
                                "confidence": 0.95,
                                "evidence_image": cnt_img,
                                "panel_evidence_image": panel_img,
                                "box_2d": cnt_box,
                                "suggested_brands": []
                            })

                        # D. Các lộ nhánh ra (Branch Feeders)
                        b_words = [w for w in c_words if w['text'] in ['MCCB', 'MCB', 'RCBO'] and 180 <= w['top'] <= 210]
                        b_words = sorted(b_words, key=lambda w: w['x0'])

                        # Lọc bỏ các điểm x0 bị trùng lặp do ký tự xếp sát nhau (< 5mm)
                        deduped_breakers: List[Any] = []
                        last_x = -999.0
                        for bw in b_words:
                            if abs(bw['x0'] - last_x) >= 5.0:
                                deduped_breakers.append(bw)
                                last_x = bw['x0']

                        for b in deduped_breakers:
                            col_x = b['x0']
                            # Lấy các từ ngữ nằm trong cột sọc dọc [col_x - 9.5, col_x + 9.5]
                            strip = [w for w in c_words if (col_x - 9.5) <= w['x0'] <= (col_x + 9.5) and 180 <= w['top'] <= 550]
                            strip = sorted(strip, key=lambda w: w['top'])

                            cat = b['text']
                            poles_str = "1P" if cat == "MCB" else "3P"
                            for w in strip:
                                if re.match(r'^(1P\+N|[1-4]P)$', w['text']):
                                    poles_str = w['text']
                                    break
                            poles_num = 2 if poles_str == "1P+N" else int(poles_str.replace("P", ""))

                            in_a = 16.0 if cat == "MCB" else 63.0
                            for w in strip:
                                m = re.match(r'^(\d{1,4})A$', w['text'])
                                if m:
                                    val = float(m.group(1))
                                    if val != 5.0:  # tránh nhầm tỷ số /5A của CT
                                        in_a = val
                                        break

                            icu_ka = 6.0 if "MCB" in cat else 18.0
                            for w in strip:
                                m = re.match(r'^(\d{1,3})kA$', w['text'])
                                if m:
                                    icu_ka = float(m.group(1))
                                    break

                            has_rcbo = cat == "RCBO" or any("30mA" in w['text'] for w in strip)
                            if has_rcbo:
                                cat = "RCBO"

                            feeder_id = ""
                            for w in strip:
                                m = re.match(r'^([PLS]\d+|E\d+)$', w['text'])
                                if m:
                                    feeder_id = m.group(1)
                                    break

                            spec = f"{poles_str} - {int(in_a)}A - {int(icu_ka)}kA" + (" - 30mA" if has_rcbo else "")
                            name = f"{cat} {poles_str} {int(in_a)}A {int(icu_ka)}kA" + (" 30mA" if has_rcbo else "")
                            if feeder_id:
                                name += f" (Lộ {feeder_id})"

                            feeder_note = f"Lộ xuất tuyến {feeder_id}" if feeder_id else "Lộ phân phối nhánh"
                            if has_rcbo:
                                feeder_note += " (Bảo vệ chống rò 30mA)"

                            # Crop cận cảnh lộ nhánh (từ thanh cái qua aptomat tới mã hiệu lộ)
                            if strip:
                                min_y = min(w['top'] for w in strip)
                                max_y = max(w['bottom'] for w in strip)
                                f_bx0 = max(x0, col_x - 30)
                                f_bx1 = min(x1, col_x + 30)
                                f_by0 = max(20.0, min_y - 30)
                                f_by1 = min(float(page.height), max_y + 35)
                                f_img, f_box = make_thumbnail(f_bx0, f_by0, f_bx1, f_by1, min_w=90.0, min_h=160.0)
                            else:
                                f_img, f_box = make_thumbnail(col_x - 30, b['top'] - 30, col_x + 30, b['top'] + 130, min_w=90.0, min_h=160.0)

                            if not f_img:
                                f_img, f_box = panel_img, panel_box

                            panel_devices.append({
                                "category": cat,
                                "name": name,
                                "spec": spec,
                                "in_a": in_a,
                                "icu_ka": icu_ka,
                                "poles": poles_num,
                                "quantity": 1,
                                "brand": "",
                                "part_number": "",
                                "section": "Đầu ra",
                                "location": f"Trang {page_num} - Bản vẽ {dwg_code} (Tủ {panel_code})",
                                "panel_code": panel_code,
                                "panel_name": panel_name,
                                "notes": feeder_note,
                                "confidence": 0.95,
                                "evidence_image": f_img,
                                "panel_evidence_image": panel_img,
                                "box_2d": f_box,
                                "suggested_brands": []
                            })

                        results.append({
                            "panel_code": panel_code,
                            "panel_name": panel_name,
                            "page_num": page_num,
                            "drawing_code": dwg_code,
                            "drawing_name": dwg_name,
                            "dimension": dim_str,
                            "dim_h": dim_h,
                            "dim_w": dim_w,
                            "dim_d": dim_d,
                            "dim_t": dim_t,
                            "notes": panel_notes,
                            "devices": panel_devices
                        })

            logger.info(f"Extracted {len(results)} panels with {sum(len(p['devices']) for p in results)} total devices from PDF")
            return results

        except PDFParsingError:
            raise
        except Exception as e:
            logger.error(f"Failed to extract multi-panel schedules: {str(e)}", exc_info=True)
            raise PDFParsingError(
                f"Lỗi khi bóc tách đa tủ từ PDF: {str(e)}",
                {"path": file_path, "error": str(e)}
            )

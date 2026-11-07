"""Extract bounded, source-attributed context from heterogeneous project files.

This module deliberately does not decide whether a file is a drawing.  It makes
all readable attachments available to the orchestration/AI layer; the role of a
file is decided against the current user request.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


class DocumentContextService:
    MAX_FILE_CHARS = 12_000
    MAX_CELL_ROWS = 250

    @staticmethod
    def _bounded(value: Any, limit: int | None = None) -> str:
        text = str(value or "").replace("\x00", " ").strip()
        return text[: limit or DocumentContextService.MAX_FILE_CHARS]

    @staticmethod
    def _read_text(path: Path) -> str:
        for encoding in ("utf-8-sig", "utf-8", "cp1258", "latin-1"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeError:
                continue
        return ""

    @staticmethod
    def _read_pdf(path: Path) -> str:
        import pymupdf
        from app.services.ingestion.drawing_reader import read_pdf_page, evidence_context

        parts: List[str] = []
        scanned_pages = 0
        with pymupdf.open(str(path)) as document:
            for index, page in enumerate(document):
                text = page.get_text(sort=True).strip()
                if text:
                    parts.append(f"[Trang {index + 1}; PyMuPDF text layer; chưa xác minh hình ảnh]\n{text}")
                elif scanned_pages < 3:
                    scanned_pages += 1
                    try:
                        evidence = read_pdf_page(path, index + 1, include_ocr=True)
                        parts.append(f"[Trang {index + 1}; OCR chưa xác minh hình ảnh]\n" + evidence_context(evidence['ocr'], 3500))
                    except Exception as exc:
                        parts.append(f"[Trang {index + 1}: OCR unavailable; cần đọc ảnh trực tiếp. {str(exc)[:250]}]")
                else:
                    parts.append(f"[Trang {index + 1} trở đi chưa OCR trong context tham chiếu; cần đọc từng trang theo phạm vi yêu cầu.]")
                    break
                if sum(len(part) for part in parts) >= DocumentContextService.MAX_FILE_CHARS:
                    parts.append('[Context bị giới hạn độ dài; chưa đọc hết tài liệu.]')
                    break
        return "\n\n".join(parts)

    @staticmethod
    def _read_docx(path: Path) -> str:
        from docx import Document

        doc = Document(str(path))
        parts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                values = [cell.text.strip() for cell in row.cells]
                if any(values):
                    parts.append(" | ".join(values))
        return "\n".join(parts)

    @staticmethod
    def _read_xlsx(path: Path) -> str:
        from openpyxl import load_workbook

        workbook = load_workbook(str(path), read_only=True, data_only=False)
        parts: List[str] = []
        try:
            for sheet in workbook.worksheets:
                parts.append(f"[Sheet: {sheet.title}]")
                for row_no, row in enumerate(sheet.iter_rows(values_only=True), 1):
                    if row_no > DocumentContextService.MAX_CELL_ROWS:
                        break
                    values = [str(value).strip() for value in row if value not in (None, "")]
                    if values:
                        parts.append(" | ".join(values))
                    if sum(len(part) for part in parts) >= DocumentContextService.MAX_FILE_CHARS:
                        break
        finally:
            workbook.close()
        return "\n".join(parts)

    @staticmethod
    def _read_delimited(path: Path) -> str:
        text = DocumentContextService._read_text(path)
        rows: List[str] = []
        try:
            dialect = csv.Sniffer().sniff(text[:4096])
            reader: Iterable[List[str]] = csv.reader(text.splitlines(), dialect)
        except csv.Error:
            reader = csv.reader(text.splitlines())
        for row_no, row in enumerate(reader, 1):
            if row_no > DocumentContextService.MAX_CELL_ROWS:
                break
            rows.append(" | ".join(str(value).strip() for value in row))
        return "\n".join(rows)

    @staticmethod
    def _read_dxf_labels(path: Path) -> str:
        """Read spatial circuit context without inferring or counting devices."""
        import re
        from app.services.ingestion.cad_parser import CadParserService
        parsed = CadParserService.parse_dxf(str(path))
        texts = parsed.texts
        blocks = parsed.blocks

        # Kiểm tra xem file CAD có chứa sơ đồ nguyên lý mạch điện (Aptomat/Cầu dao) không
        breakers = [t for t in texts if any(k in t['text'].upper() for k in ('MCB', 'MCCB', 'RCBO', 'RCCB'))]
        if breakers:
            # Sơ đồ nguyên lý điện: nhóm và tổng hợp theo từng tủ điện một cách trực quan, đầy đủ
            titles = [t for t in texts if 'SƠ ĐỒ NGUYÊN LÝ' in t['text'].upper() and t['x'] < 25000]
            titles.sort(key=lambda t: -t['y'])
            sections = []
            if titles:
                sections.append((titles[0], 1e9, titles[1]['y'] if len(titles) > 1 else -1e9))
                for i in range(1, len(titles)):
                    ymax = titles[i]['y']
                    ymin = titles[i+1]['y'] if i + 1 < len(titles) else -1e9
                    sections.append((titles[i], ymax, ymin))
            else:
                sections.append((None, 1e9, -1e9))

            out = [f"=== DỮ LIỆU SƠ ĐỒ NGUYÊN LÝ CAD ({len(sections)} TỦ ĐIỆN, TỔNG {len(breakers)} THIẾT BỊ ĐÓNG CẮT) ==="]
            for idx, (title_obj, ymax, ymin) in enumerate(sections, 1):
                ptexts = [t for t in texts if ymin <= t['y'] < ymax]
                pbreakers = [t for t in breakers if ymin <= t['y'] < ymax]
                raw_title = title_obj['text'] if title_obj else f'Tủ điện số {idx}'
                panel_title = re.sub(r'%%[uU]', '', raw_title).strip()

                enclosure = [t['text'] for t in ptexts if any(k in t['text'].upper() for k in ('KT:', 'TÔN', '2 LỚP CÁNH', 'SƠN TĨNH ĐIỆN'))]
                enclosure_str = ', '.join(dict.fromkeys(enclosure)) if enclosure else 'Theo tiêu chuẩn'

                metering = [t['text'] for t in ptexts if any(k in t['text'].upper() for k in ('ĐỒNG HỒ', 'ĐÈN BÁO', 'TI ', '/5A', 'CẦU CHÌ', '3X2A'))]
                metering_str = ', '.join(dict.fromkeys(metering)) if metering else ''

                incomers = [b for b in pbreakers if b['x'] < 28000 or any(k in b['text'].upper() for k in ('400A', 'INCOMING', 'TỔNG', 'CẤP ĐẾN'))]
                branches = [b for b in pbreakers if b not in incomers]

                out.append(f"\n[TỦ {idx}] {panel_title}:")
                out.append(f"  - Kích thước & thông số vỏ tủ: {enclosure_str}")
                if metering_str:
                    out.append(f"  - Đo lường & phụ kiện: {metering_str}")

                inc_cables = [t['text'] for t in ptexts if any(k in t['text'].upper() for k in ('CẤP ĐẾN', 'CÔNG SUẤT TÍNH TOÁN', 'PTT:'))]
                if incomers:
                    inc_spec = incomers[0]['text'].strip()
                    inc_cable_str = ' | '.join(inc_cables[:2]) if inc_cables else ''
                    out.append(f"  - Thiết bị bảo vệ đầu vào (Incomer): {inc_spec}" + (f" ({inc_cable_str})" if inc_cable_str else ""))

                out.append(f"  - Danh sách {len(branches)} lộ xuất tuyến / thiết bị nhánh:")
                branches.sort(key=lambda b: -b['y'])
                for b in branches:
                    row_items = [t for t in ptexts if abs(t['y'] - b['y']) <= 500 and t['x'] > b['x'] and t['x'] < 52000]
                    row_items.sort(key=lambda t: t['x'])
                    load_items = [t for t in ptexts if abs(t['y'] - b['y']) <= 600 and t['x'] >= 52000]
                    load_str = ' '.join(dict.fromkeys(t['text'].strip() for t in load_items)) or 'Phụ tải nhánh'

                    tag = next((re.match(r'^(?:[A-Z]{1,3}\d+|DP)$', it['text'].strip(), re.I).group(0).upper()
                                for it in row_items if re.match(r'^(?:[A-Z]{1,3}\d+|DP)$', it['text'].strip(), re.I)), '')
                    cable = next((it['text'].strip() for it in row_items if 'CU/' in it['text'].upper() or 'MM2' in it['text'].upper()), '')
                    power = next((it['text'].strip() + ' kW' for it in row_items if re.match(r'^\d+(?:\.\d+)?$', it['text'].strip())), '')

                    parts = []
                    if tag: parts.append(f"Tag: {tag}")
                    parts.append(b['text'].strip())
                    if power: parts.append(power)
                    if cable: parts.append(cable)
                    parts.append(f"Phụ tải: {load_str}")
                    out.append("    + " + " | ".join(parts))

            # Kèm tọa độ gốc để đối chiếu khi cần
            rows = [(row['x'], row['y'], row['text'], row['layer']) for row in texts]
            rows.extend((row['x'], row['y'], 'BLOCK ' + row['name'], row['layer']) for row in blocks)
            rows.sort(key=lambda row: (round(row[0] / 60), -row[1]))
            out.append("\n=== TOẠ ĐỘ CHI TIẾT CÁC ĐỐI TƯỢNG CAD ===")
            out.append("\n".join(f"X={x:g} Y={y:g} [{layer}] {value}" for x, y, value, layer in rows))
            return "\n".join(out)

        rows = [(row['x'], row['y'], row['text'], row['layer']) for row in texts]
        rows.extend((row['x'], row['y'], 'BLOCK ' + row['name'], row['layer']) for row in blocks)
        rows.sort(key=lambda row: (round(row[0] / 60), -row[1]))
        return "\n".join(f"X={x:g} Y={y:g} [{layer}] {value}" for x, y, value, layer in rows)

    @staticmethod
    def extract(file_obj: Any) -> Dict[str, Any]:
        filename = str(getattr(file_obj, "filename", "") or "")
        path = Path(str(getattr(file_obj, "file_path", "") or ""))
        ext = path.suffix.lower().lstrip(".") or filename.rsplit(".", 1)[-1].lower()
        result: Dict[str, Any] = {
            "file_id": getattr(file_obj, "id", None),
            "filename": filename,
            "extension": ext,
            "mime_type": str(getattr(file_obj, "file_type", "") or ""),
            "exists": path.is_file(),
            "text": "",
            "read_error": "",
        }
        if not path.is_file():
            result["read_error"] = "file_not_found"
            return result

        try:
            if ext == "pdf":
                text = DocumentContextService._read_pdf(path)
            elif ext in {"png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"}:
                from app.services.ingestion.drawing_reader import read_image, evidence_context
                text = 'PaddleOCR — dữ liệu nguồn chưa xác minh hình ảnh:\n' + evidence_context(read_image(path), 11000)
            elif ext in {"dxf", "dwg"}:
                from app.services.ingestion.cad_parser import CadParserService
                analysis_path = Path(CadParserService.prepare_analysis_path(str(path)))
                text = DocumentContextService._read_dxf_labels(analysis_path)
            elif ext == "docx":
                text = DocumentContextService._read_docx(path)
            elif ext in {"xlsx", "xlsm"}:
                text = DocumentContextService._read_xlsx(path)
            elif ext in {"csv", "tsv"}:
                text = DocumentContextService._read_delimited(path)
            elif ext == "json":
                parsed = json.loads(DocumentContextService._read_text(path))
                text = json.dumps(parsed, ensure_ascii=False, indent=2)
            elif ext in {"txt", "md", "log", "xml", "html", "yaml", "yml"}:
                text = DocumentContextService._read_text(path)
            else:
                text = ""
            result["text"] = DocumentContextService._bounded(text)
        except Exception as exc:  # optional readers must not discard the attachment
            result["read_error"] = f"{type(exc).__name__}: {exc}"[:500]
        return result

    @staticmethod
    def build_prompt_context(contexts: List[Dict[str, Any]], max_total_chars: int = 30_000) -> str:
        blocks: List[str] = []
        used = 0
        for context in contexts:
            text = str(context.get("text") or "").strip()
            if not text:
                continue
            header = f"--- TỆP THAM CHIẾU: {context.get('filename') or 'không tên'} ---\n"
            remaining = max_total_chars - used - len(header)
            if remaining <= 0:
                break
            block = header + text[:remaining]
            blocks.append(block)
            used += len(block)
        return "\n\n".join(blocks)

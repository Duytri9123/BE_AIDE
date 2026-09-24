"""Whole-document circuit assessment before any device takeoff."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.ingestion.document_context import DocumentContextService
from app.services.ai.connection_pool import ConnectionPoolService
from app.services.ai.response_parser import ResponseParserService
from app.services.ai.vision_analyzer import VisionAnalyzerService


PREFLIGHT_INSTRUCTIONS = """Bạn là kỹ sư điện đang đọc TOÀN BỘ hồ sơ trước bước bóc tách.
Hãy xác định vai trò từng tệp, ranh giới sơ đồ nguyên lý, nguồn cấp, tải, mạch đo lường,
điều khiển, bảo vệ, liên hệ giữa các trang/tủ và các cụm có nhiều phần tử.
Đồng hồ chung chung có thể là ampe kế, vôn kế, đồng hồ đa năng hoặc công tơ; khởi động từ
có thể thuộc mạch sao-tam giác, đảo chiều hoặc đóng cắt đơn. Chỉ xác định chức năng khi
đường dây, tag, ký hiệu hay ghi chú hỗ trợ; nếu thiếu hãy nêu các khả năng và thông tin cần tra.
Tiếp địa, thanh nối đất, cầu đấu và phụ kiện lắp đặt có thể cần thiết dù không có tag BOM;
ghi ở installation_considerations với trạng thái đề xuất, không nhận là thiết bị đã thấy.
Không lập BOM, không đếm thiết bị, không chọn SKU, không tạo CAD ở bước này.
Trả đúng một JSON: {"circuit_summary":"", "file_roles":[], "circuits":[],
"functional_groups":[], "ambiguous_symbols":[], "installation_considerations":[],
"questions":[], "source_limits":[]}.
Mỗi kết luận phải có nguồn tệp/trang/tag khi thấy rõ. Viết tiếng Việt. Không suy đoán thành sự thật.
"""


class CircuitPreflightService:
    @staticmethod
    def _context(contexts: list[dict[str, Any]]) -> str:
        parts = []
        for row in contexts:
            filename = row.get('filename') or ''
            text = str(row.get('text') or '').strip()
            if text:
                parts.append(f"[{filename}]\n{text[:10000]}")
        return '\n\n'.join(parts)[:24000]

    @staticmethod
    async def assess(files, contexts, db, connections, user_prompt='') -> dict[str, Any]:
        context = CircuitPreflightService._context(contexts)
        prompt = PREFLIGHT_INSTRUCTIONS + f"\nYêu cầu của người dùng: {user_prompt or 'Đọc sơ đồ trước khi bóc tách.'}\n"
        source_type = 'text'
        if context:
            prompt += f"\nThông tin đọc được từ các tệp:\n{context}"
            call_fn = VisionAnalyzerService.analyze_text
            args = {'prompt': prompt}
        else:
            image = next((str(f.file_path) for f in files
                          if Path(str(f.file_path)).suffix.lower() in {'.png','.jpg','.jpeg','.webp','.bmp'}
                          and Path(str(f.file_path)).is_file()), None)
            if not image:
                return {'status': 'unavailable', 'circuit_summary': '', 'source_limits': ['Chưa đọc được ngữ cảnh toàn hồ sơ.']}
            source_type = 'image'
            call_fn = VisionAnalyzerService.analyze_image
            args = {'image_path': image, 'prompt': prompt}
        if not db or not connections:
            return {'status': 'unavailable', 'circuit_summary': '', 'source_limits': ['Chưa có kết nối AI để đánh giá sơ đồ.']}
        response, _ = await ConnectionPoolService.call_with_fallback(
            db=db, connections=connections, call_fn=call_fn, **args)
        parsed = next((block for block in ResponseParserService.extract_json_blocks(response)
                       if isinstance(block, dict) and 'circuit_summary' in block), None)
        if not parsed:
            return {'status': 'unavailable', 'circuit_summary': '', 'source_limits': ['AI chưa trả được đánh giá sơ đồ có cấu trúc.']}
        result = {key: parsed.get(key, [] if key != 'circuit_summary' else '')
                  for key in ('circuit_summary','file_roles','circuits','functional_groups',
                              'ambiguous_symbols','installation_considerations','questions','source_limits')}
        result['status'] = 'assessed'
        result['source_type'] = source_type
        return result

    @staticmethod
    def extraction_context(assessment: dict[str, Any]) -> str:
        if assessment.get('status') != 'assessed':
            return ''
        bounded = {key: assessment.get(key) for key in ('circuit_summary','file_roles','circuits',
                    'functional_groups','ambiguous_symbols','installation_considerations','questions')}
        return ('ĐÁNH GIÁ SƠ ĐỒ TOÀN HỒ SƠ ĐÃ HOÀN THÀNH TRƯỚC BÓC TÁCH:\n'
                + json.dumps(bounded, ensure_ascii=False)[:12000]
                + '\nĐây là ngữ cảnh kiểm tra, không phải danh sách thiết bị đã quan sát. '
                  'Chỉ thêm vào BOM thiết bị có căn cứ trong sơ đồ hoặc ghi chú cụ thể; '
                  'các chi tiết lắp đặt suy luận để ở đề xuất kỹ thuật, không tự thêm như đã vẽ.')

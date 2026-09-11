"""
Dynamic Equipment & Technical Proposal Helper
---------------------------------------------
Mô-đun hỗ trợ xử lý cấu trúc dữ liệu thiết bị đi kèm và đề xuất tương thích kỹ thuật.
Toàn bộ phân tích kỹ thuật, phát hiện thông số đặc thù và đề xuất giải pháp đều do
AI Vision / LLM phân tích trực tiếp từ sơ đồ nguyên lý (SLD) của bản vẽ,
không sử dụng bất kỳ quy tắc hard-code nào.
"""
from typing import List, Dict, Any, Optional

class AccompanyingEquipmentService:
    """Helper xử lý danh mục phụ kiện đi kèm theo phân tích của AI."""

    @staticmethod
    def format_accessories(
        accessories: Optional[List[Dict[str, Any]]],
        parent_brand: Optional[str] = None,
        parent_category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Chuẩn hóa dữ liệu phụ kiện do AI trả về."""
        if not accessories:
            return []
        formatted = []
        for idx, acc in enumerate(accessories, 1):
            if not isinstance(acc, dict):
                continue
            evidence = (
                acc.get("evidence")
                or acc.get("sld_evidence")
                or acc.get("source_reference")
            )
            # Safety boundary: an accessory must be traceable to the supplied
            # schematic. Functional convention alone is not enough evidence.
            if not str(evidence or "").strip():
                continue
            name = acc.get("name") or "Phụ kiện đi kèm"
            if not name.startswith("↳") and "[Thiết bị đi kèm]" not in name:
                display_name = f"   ↳ [Thiết bị đi kèm] {name}"
            else:
                display_name = name

            category = acc.get("category")
            if not category:
                category = f"Phụ kiện {parent_category}" if parent_category else "Phụ kiện đi kèm"

            brand = acc.get("brand") or parent_brand or ""

            formatted.append({
                "code": acc.get("code") or f"ACC_{idx}",
                "name": display_name,
                "category": category,
                "brand": brand,
                "spec": acc.get("spec") or "",
                "sku": acc.get("sku") or "-",
                "origin": acc.get("origin") or "VN",
                "unit": acc.get("unit") or "Bộ",
                "quantity": int(acc.get("quantity") or 1),
                "unit_price": int(acc.get("unit_price") or 0),
                # Keep the AI's engineering explanation so the UI can show
                # why this accessory belongs to its parent device.
                "notes": acc.get("notes") or acc.get("technical_reason") or acc.get("reason") or "",
                "technical_reason": acc.get("technical_reason") or acc.get("reason") or acc.get("notes") or "",
                "evidence": str(evidence).strip()
            })
        return formatted


class CompatibleAlternativeService:
    """Helper xử lý dữ liệu đề xuất tương thích kỹ thuật do AI sinh ra."""

    @staticmethod
    def format_proposal(proposal: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Chuẩn hóa cấu trúc đề xuất tương thích từ AI."""
        if not proposal or not isinstance(proposal, dict):
            return None
        return {
            "original_device": proposal.get("original_device") or "",
            "original_spec": proposal.get("original_spec") or "",
            "ai_analysis": proposal.get("ai_analysis") or "",
            "proposed_device": proposal.get("proposed_device") or "",
            "proposed_spec": proposal.get("proposed_spec") or "",
            "suggested_brand": proposal.get("suggested_brand") or "",
            "technical_reason": proposal.get("technical_reason") or "Bảo toàn 100% sơ đồ nguyên lý"
        }

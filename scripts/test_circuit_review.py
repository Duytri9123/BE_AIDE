"""Offline checks for circuit findings, page identity and partial visual review."""
import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch
from PIL import Image
from app.services.ai.system_completeness import technical_audit
from app.services.ai.circuit_preflight import CircuitPreflightService
from app.api.v1.endpoints.analyze import _build_analysis_result_schema
from app.services.ai.analysis_pipeline_service import AnalysisPipelineService
from app.schemas.ai import ExtractedDeviceSchema
from uuid import uuid4
from pathlib import Path
import tempfile


def device(tag="Q1", **kwargs):
    values = dict(category="MCB", name="MCB", spec="3P 20A 6kA", tag=tag,
                panel_code="P", source_filename="drawing.pdf", source_page=1,
                poles=3, in_a=20, icu_ka=6)
    values.update(kwargs)
    return values


class CircuitReviewTests(unittest.TestCase):
    def test_busbar_and_described_existing_tag_are_not_missing_devices(self):
        from app.services.ai.system_completeness import review_system
        rows = [device('Q1'), device('Q2', upstream_device='Thanh cái chính'),
                device('Q3', upstream_device='MCCB tổng Q1'),
                device('Q4', upstream_device='Q99')]
        issues = [i for i in review_system(rows)['issues']
                  if i['title'] == 'Chưa tìm thấy thiết bị cấp nguồn']
        self.assertEqual(len(issues), 1)

    def test_pdf_previews_keep_page_identity_in_api(self):
        image1, image2 = "data:image/jpeg;base64," + "a" * 120, "data:image/jpeg;base64," + "b" * 120
        result = _build_analysis_result_schema(uuid4(), 1, [device(panel_evidence_image=image1), device(source_page=2, panel_evidence_image=image2)], enclosure_spec={"incomer_rating": 20})
        self.assertEqual(result.panel_images["drawing.pdf::page::1"], image1)
        self.assertEqual(result.panel_images["drawing.pdf::page::2"], image2)

    def test_unlocated_device_can_still_open_its_source_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.png"
            Image.new("RGB", (200, 100), "white").save(path)
            rows = [ExtractedDeviceSchema(**device("Q1")), ExtractedDeviceSchema(**device("Q2"))]
            AnalysisPipelineService._attach_evidence_thumbnails(rows, str(path))
            self.assertTrue(all(d.panel_evidence_image for d in rows))
            self.assertTrue(all(d.evidence_image is None for d in rows))

    def test_cycle_is_review_not_design_error(self):
        audit = technical_audit([device("Q1", upstream_device="Q2"), device("Q2", upstream_device="Q1")])
        cycle = next(i for i in audit["missing_items"] if i["title"] == "Liên kết nguồn tạo vòng")
        self.assertEqual(cycle["certainty"], "suspected")
        self.assertTrue(cycle["recommendation"])
        self.assertFalse(audit["release_ready"])

    def test_normal_chain_has_no_cycle(self):
        audit = technical_audit([device("Q1"), device("Q2", upstream_device="Q1")])
        self.assertNotIn("Liên kết nguồn tạo vòng", [i["title"] for i in audit["missing_items"]])

    def test_ambiguous_tag_does_not_establish_cycle(self):
        audit = technical_audit([device("Q1", upstream_device="Q1"), device("Q1")])
        duplicate = next(i for i in audit["missing_items"] if i["title"] == "Ký hiệu thiết bị bị trùng")
        self.assertIsNone(duplicate["source_filename"])
        self.assertNotIn("Liên kết nguồn tạo vòng", [i["title"] for i in audit["missing_items"]])

    def test_bad_catalog_rating_is_actionable(self):
        audit = technical_audit([device(brand="LS", catalog_matches={"LS": {"sku": "X", "icu": 4.5, "meets_icu": False}})])
        issue = next(i for i in audit["missing_items"] if i["severity"] == "critical")
        self.assertEqual(issue["source_page"], 1)
        self.assertTrue(issue["required_information"])
        self.assertIn("Loại mã", issue["recommendation"])

    def test_visual_findings_bound_to_actual_page(self):
        result = {"findings": [{"title": "Điểm nối", "source_filename": "wrong.png", "source_page": 99,
                                "box_2d": [100, 100, 200, 200], "certainty": "approved"}]}
        CircuitPreflightService._bind_findings(result, "drawing.pdf / trang 2")
        item = result["findings"][0]
        self.assertEqual((item["source_filename"], item["source_page"]), ("drawing.pdf", 2))
        self.assertEqual(item["certainty"], "suspected")

    def test_invalid_finding_box_is_unlocated(self):
        result = {"findings": [{"title": "A", "box_2d": [100, 100, 100, 200]}, "bad"]}
        CircuitPreflightService._bind_findings(result, "source.png")
        self.assertEqual(len(result["findings"]), 1)
        self.assertIsNone(result["findings"][0]["box_2d"])

    def test_one_unreadable_page_preserves_other_findings(self):
        response = json.dumps({"circuit_summary": "Mạch nguồn", "has_sld": True,
                               "findings": [{"title": "Kiểm tra nối dây"}]})
        pages = [("drawing.pdf / trang 1", Image.new("RGB", (400, 300))),
                 ("drawing.pdf / trang 2", Image.new("RGB", (400, 300)))]
        call = AsyncMock(side_effect=[(response, None), RuntimeError("offline")])
        with patch.object(CircuitPreflightService, "_visual_pages", return_value=pages), \
             patch("app.services.ai.circuit_preflight.ConnectionPoolService.call_with_fallback", call):
            result = asyncio.run(CircuitPreflightService.assess([], [], object(), [object()]))
        self.assertEqual(result["status"], "assessed")
        self.assertEqual(len(result["findings"]), 1)
        self.assertTrue(result["source_limits"])
        self.assertEqual(call.await_count, 2)


if __name__ == "__main__":
    unittest.main()

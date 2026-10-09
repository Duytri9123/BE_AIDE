import unittest
from app.services.ai.analysis_pipeline_service import AnalysisPipelineService as Pipeline


class FocusedEvidenceTests(unittest.TestCase):
    def test_small_label_includes_readable_circuit_context(self):
        crop = Pipeline._evidence_crop_pixels([315, 169, 335, 245], 1684, 2382)
        self.assertGreater(crop[2]-crop[0], 350)
        self.assertGreater(crop[3]-crop[1], 250)
        self.assertLess(crop[2]-crop[0], 1684)
        self.assertLess(crop[3]-crop[1], 2382)

    def test_crop_is_clamped_to_page_edges(self):
        self.assertEqual(Pipeline._evidence_crop_pixels([0, 0, 1000, 1000], 100, 100), (0, 0, 100, 100))

    def test_invalid_or_subpixel_boxes_do_not_produce_fake_evidence(self):
        for box in ([50, 30, 20, 10], [10, 10, 10, 20], ['x', 0, 100, 100], [0, 0, 1, 1]):
            self.assertIsNone(Pipeline._evidence_crop_pixels(box, 100, 100))


if __name__ == '__main__':
    unittest.main()

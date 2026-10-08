import unittest
from app.services.ai.analysis_pipeline_service import AnalysisPipelineService as Pipeline


class FocusedEvidenceTests(unittest.TestCase):
    def test_small_symbol_crop_does_not_expand_to_a_page_region(self):
        crop = Pipeline._evidence_crop_pixels([315, 169, 335, 245], 1684, 2382)
        self.assertLess(crop[2]-crop[0], 200)
        self.assertLess(crop[3]-crop[1], 85)
        # Adjacent lamps start below the MCCB: the preview must stop before them.
        self.assertLess(crop[3], 343*2382/1000)

    def test_crop_is_clamped_to_page_edges(self):
        self.assertEqual(Pipeline._evidence_crop_pixels([0, 0, 1000, 1000], 100, 100), (0, 0, 100, 100))

    def test_invalid_or_subpixel_boxes_do_not_produce_fake_evidence(self):
        for box in ([50, 30, 20, 10], [10, 10, 10, 20], ['x', 0, 100, 100], [0, 0, 1, 1]):
            self.assertIsNone(Pipeline._evidence_crop_pixels(box, 100, 100))


if __name__ == '__main__':
    unittest.main()

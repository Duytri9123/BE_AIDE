import unittest
from app.services.ai.analysis_pipeline_service import AnalysisPipelineService as Pipeline


class FocusedEvidenceTests(unittest.TestCase):
    def test_wide_and_tall_regions_keep_all_verified_content(self):
        for box in ([100, 100, 150, 700], [100, 100, 800, 150]):
            left, top, right, bottom = Pipeline._evidence_crop_pixels(box, 1000, 1000)
            self.assertLessEqual(left, box[1])
            self.assertLessEqual(top, box[0])
            self.assertGreaterEqual(right, box[3])
            self.assertGreaterEqual(bottom, box[2])
            self.assertNotEqual(right-left, bottom-top)

    def test_verified_device_crop_excludes_neighbouring_circuits(self):
        crop = Pipeline._evidence_crop_pixels([315, 169, 335, 245], 1684, 2382)
        self.assertLess(crop[2]-crop[0], 150)
        self.assertLess(crop[3]-crop[1], 90)
        self.assertLess(crop[2]-crop[0], 1684)
        self.assertLess(crop[3]-crop[1], 2382)

    def test_crop_is_clamped_to_page_edges(self):
        self.assertEqual(Pipeline._evidence_crop_pixels([0, 0, 1000, 1000], 100, 100), (0, 0, 100, 100))

    def test_invalid_or_subpixel_boxes_do_not_produce_fake_evidence(self):
        for box in ([50, 30, 20, 10], [10, 10, 10, 20], ['x', 0, 100, 100], [0, 0, 1, 1]):
            self.assertIsNone(Pipeline._evidence_crop_pixels(box, 100, 100))


if __name__ == '__main__':
    unittest.main()

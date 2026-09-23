"""Focused regression tests for cabinet quotation/layout behavior."""

import unittest

import ezdxf

from app.services.export.dynamic_grouping import DynamicGroupingEngine
from app.services.ai.analysis_pipeline_service import AnalysisPipelineService
from app.services.cad.enclosure_cad_generator import (
    EnclosureCadGeneratorService,
    setup_cad_layers,
)


class DynamicGroupingAccessoryTests(unittest.TestCase):
    def test_duplicate_devices_keep_and_sum_attached_accessories(self):
        devices = [
            {
                "name": "MCB LS BKN 1P 16A - Lộ 1",
                "category": "MCB",
                "spec": "1P 16A",
                "part_number": "BKN-b-1P-16A",
                "brand": "LS",
                "quantity": 1,
                "accompanying_accessories": [
                    {"code": "AUX-LS", "name": "Tiếp điểm phụ", "quantity": 1}
                ],
            },
            {
                "name": "MCB LS BKN 1P 16A - Lộ 2",
                "category": "MCB",
                "spec": "1P 16A",
                "part_number": "BKN-b-1P-16A",
                "brand": "LS",
                "quantity": 1,
                "accompanying_accessories": [
                    {"code": "AUX-LS", "name": "Tiếp điểm phụ", "quantity": 1}
                ],
            },
        ]

        merged = DynamicGroupingEngine.merge_duplicates(devices)

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["quantity"], 2)
        self.assertEqual(merged[0]["accompanying_accessories"], [
            {"code": "AUX-LS", "name": "Tiếp điểm phụ", "quantity": 2}
        ])


    def test_different_accessories_remain_attached_to_merged_parent(self):
        devices = [
            {
                "name": "Contactor LS MC-18 - Nhánh 1",
                "category": "CONTACTOR",
                "spec": "18A",
                "part_number": "MC-18",
                "quantity": 1,
                "accompanying_accessories": [
                    {"code": "AUX-1NO", "name": "Tiếp điểm 1NO", "quantity": 1}
                ],
            },
            {
                "name": "Contactor LS MC-18 - Nhánh 2",
                "category": "CONTACTOR",
                "spec": "18A",
                "part_number": "MC-18",
                "quantity": 1,
                "accompanying_accessories": [
                    {"code": "COIL-220", "name": "Cuộn coil 220V", "quantity": 1}
                ],
            },
        ]

        merged = DynamicGroupingEngine.merge_duplicates(devices)

        self.assertEqual(len(merged), 1)
        self.assertEqual(
            [item["code"] for item in merged[0]["accompanying_accessories"]],
            ["AUX-1NO", "COIL-220"],
        )


class MultiPanelQuotationTests(unittest.TestCase):
    def test_duplicate_panel_fragments_are_consolidated_and_no_device_is_dropped(self):
        panels = [
            {
                "panel_code": "DB-LS",
                "panel_name": "Tủ LS",
                "dim_h": 1200,
                "dim_w": 700,
                "dim_d": 250,
                "devices": [
                    {
                        "tag": "QF1",
                        "name": "MCCB LS tổng",
                        "category": "MCCB",
                        "section": "Đầu vào",
                        "in_a": 100,
                        "poles": 3,
                        "part_number": "ABN103c",
                        "brand": "LS",
                        "quantity": 1,
                        "accompanying_accessories": [
                            {"code": "AX", "name": "Tiếp điểm phụ AX", "quantity": 1}
                        ],
                    }
                ],
            },
            {
                "panel_code": "DB-LS",
                "panel_name": "Tủ LS",
                "devices": [
                    {
                        "tag": "FAN1",
                        "name": "Quạt thông gió tủ",
                        "category": "FAN",
                        "section": "Khác",
                        "part_number": "FAN-01",
                        "quantity": 1,
                    },
                    {
                        "tag": "QF2",
                        "name": "MCB LS nhánh",
                        "category": "MCB",
                        "section": "Nhánh ổ cắm",
                        "in_a": 16,
                        "poles": 1,
                        "part_number": "BKN-1P-16",
                        "brand": "LS",
                        "quantity": 1,
                    },
                ],
            },
        ]

        rows = AnalysisPipelineService._build_quotation_rows(
            project_name="Dự án kiểm thử",
            extracted_devices=[],
            device_price_map={"ABN103c": 100, "FAN-01": 20, "BKN-1P-16": 10},
            enclosure_spec={"height": 1200, "width": 700, "depth": 250, "thickness": 1.5},
            enclosure_unit_price=0,
            busbar_unit_price=0,
            multi_panel_list=panels,
        )

        self.assertEqual(sum(row["row_type"] == "panel_header" for row in rows), 1)
        item_names = [row.get("name") for row in rows if row.get("row_type") in ["item", "accessory"]]
        for expected in ["MCCB LS tổng", "Tiếp điểm phụ AX", "Quạt thông gió tủ", "MCB LS nhánh"]:
            self.assertIn(expected, item_names)
        parent_index = item_names.index("MCCB LS tổng")
        self.assertEqual(item_names[parent_index + 1], "Tiếp điểm phụ AX")


class DxfBomTests(unittest.TestCase):
    def test_dxf_bom_keeps_all_rows_and_places_accessory_after_parent(self):
        devices = [
            {
                "tag": "QF1",
                "name": "MCCB LS tổng",
                "category": "MCCB",
                "section": "Đầu vào",
                "in_a": 100,
                "poles": 3,
                "brand": "LS",
                "part_number": "ABN103c",
                "quantity": 1,
                "accompanying_accessories": [
                    {"code": "AX", "name": "Tiếp điểm phụ AX", "quantity": 1}
                ],
            }
        ]
        devices.extend(
            {
                "tag": f"QF{index}",
                "name": f"MCB LS NHANH {index}",
                "category": "MCB",
                "section": "Đầu ra",
                "in_a": 16,
                "poles": 1,
                "brand": "LS",
                "part_number": f"BKN-{index}",
                "quantity": 1,
            }
            for index in range(2, 20)
        )
        specs = EnclosureCadGeneratorService.calculate_enclosure_specs(
            devices, preferred_dimensions=(2200, 1200, 400)
        )
        doc = ezdxf.new("R2010", setup=True)
        setup_cad_layers(doc)

        EnclosureCadGeneratorService._draw_single_panel(
            msp=doc.modelspace(),
            devices=devices,
            panel_code="DB-LS",
            panel_name="Tủ LS",
            specs=specs,
        )

        table_texts = [
            entity.dxf.text
            for entity in doc.modelspace().query('TEXT[layer=="0_TEXT"]')
        ]
        enclosure_index = next(i for i, text in enumerate(table_texts) if text.startswith("VO TU DIEN DB-LS"))
        incomer_index = next(i for i, text in enumerate(table_texts) if "[QF1] MCCB LS TONG" in text)
        accessory_index = next(i for i, text in enumerate(table_texts) if "TIEP DIEM PHU AX" in text)
        self.assertLess(enclosure_index, incomer_index)
        self.assertEqual(accessory_index, incomer_index + 7)
        self.assertTrue(any("MCB LS NHANH 19" in text for text in table_texts))


class CatalogDrivenSizingTests(unittest.TestCase):
    @staticmethod
    def _tt_devices():
        devices = [{
            "tag": "QF0", "name": "MCCB tổng 630A 65kA", "category": "MCCB",
            "section": "INCOMER", "brand": "LS", "poles": 3, "in_a": 630, "icu_ka": 65,
        }]
        devices.extend({
            "tag": f"QF{i}", "name": f"MCCB nhánh {i}", "category": "MCCB",
            "brand": "LS", "poles": 3, "in_a": 125, "icu_ka": 25,
        } for i in range(1, 9))
        devices.extend([
            {"tag": "QF9", "name": "3x MCB 1P 16A", "category": "MCB", "brand": "LS", "poles": 3, "in_a": 16, "icu_ka": 6},
            {"tag": "QF10", "name": "3x MCB 1P 16A", "category": "MCB", "brand": "LS", "poles": 3, "in_a": 16, "icu_ka": 6},
            {"tag": "QF11", "name": "MCB 3P 32A", "category": "MCB", "brand": "LS", "poles": 3, "in_a": 32, "icu_ka": 6},
            {"tag": "QF12", "name": "MCCB dự phòng", "category": "MCCB", "brand": "LS", "poles": 3, "in_a": 125, "icu_ka": 25},
        ])
        return devices

    def test_tt_uses_catalog_envelopes_and_matches_reference_size(self):
        specs = EnclosureCadGeneratorService.calculate_enclosure_specs(self._tt_devices())

        self.assertEqual((specs["height"], specs["width"], specs["depth"]), (1600.0, 1000.0, 450.0))
        self.assertEqual(specs["layout_style"], "CENTRAL_VERTICAL_BUSBAR")
        self.assertEqual(specs["doors"], 1)
        self.assertIn("60x8.0mm", specs["busbar_spec"])
        self.assertTrue(specs["fit_check"]["catalog_warnings"])

    def test_too_small_template_is_expanded_instead_of_forced(self):
        specs = EnclosureCadGeneratorService.calculate_enclosure_specs(
            self._tt_devices(), preferred_dimensions=(1200, 800, 300)
        )

        self.assertEqual((specs["height"], specs["width"], specs["depth"]), (1600.0, 1000.0, 450.0))
        self.assertFalse(specs["fit_check"]["preferred_dimensions_fit"])

    def test_small_panel_does_not_inherit_large_panel_dimensions(self):
        devices = [
            {"tag": "QF0", "name": "MCB tổng", "category": "MCB", "section": "INCOMER", "brand": "LS", "poles": 3, "in_a": 63, "icu_ka": 6},
            *[
                {"tag": f"QF{i}", "name": f"MCB nhánh {i}", "category": "MCB", "brand": "LS", "poles": 1, "in_a": 16, "icu_ka": 6}
                for i in range(1, 5)
            ],
        ]

        specs = EnclosureCadGeneratorService.calculate_enclosure_specs(devices)

        self.assertEqual(specs["layout_style"], "HORIZONTAL_ROWS")
        self.assertLessEqual(specs["width"], 500)
        self.assertLessEqual(specs["height"], 600)
        self.assertLessEqual(specs["depth"], 300)


if __name__ == "__main__":
    unittest.main()

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


if __name__ == "__main__":
    unittest.main()

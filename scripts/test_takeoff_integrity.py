import json
import unittest
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from app.schemas.ai import ExtractedDeviceSchema as Device
from app.services.ai.analysis_pipeline_service import AnalysisPipelineService as Pipeline
from app.services.ai.takeoff_integrity import normalize_takeoff
from app.services.ai.procurement_review import build_quotation_rows
from app.services.ai.system_completeness import technical_audit
from app.services.device_catalog_engine import DeviceCatalogEngine
from app.services.ai.response_parser import ResponseParserService as Parser


def device(**kw):
    return Device(**dict(category='FUSE',name='Cầu chì',spec='1x6A',quantity=1,
                         panel_code='P',source_filename='source.jpg',**kw))


class IntegrityTests(unittest.TestCase):
    def test_measurement_references_and_explicit_brand_policy(self):
        engine = DeviceCatalogEngine.get_instance()
        engine.load_reference_profiles()
        for category, fragment in [('LIGHT', 'CHINT_DenBaoPha'), ('METER', 'VonKeKim'), ('SELECTOR', 'ChuyenMachVon')]:
            refs = engine.search_references(category, limit=100)
            self.assertTrue(any(fragment in p['reference_path'] for p in refs))
            self.assertTrue(all(p['sku'] is None and p['price'] is None for p in refs))
        self.assertEqual(engine.search_references('METER', 'LS'), [])
        refs = engine.search_references('METER', 'LS', allow_other_brands=True)
        self.assertTrue(refs)
        self.assertTrue(all(p['brand_match'] == 'alternative_requires_confirmation' for p in refs))

    def test_half_quoted_key_keeps_whole_fenced_envelope(self):
        s='```json\n{"warnings":["x"],"devices":[{"category":"LIGHT","name":"R",spec":"LED"},{"category":"MCB","name":"Q","spec":"2P"}]}\n```'
        self.assertEqual(len(Parser.parse_device_list(s)),2)
        bad='```json\n{"warnings":["x"],"devices":[garbage]}\n```'
        self.assertEqual(Parser.extract_json_blocks(bad),[])
    def test_quotation_survives_missing_cad_dimensions(self):
        db=SimpleNamespace(execute=AsyncMock(),commit=AsyncMock(),flush=AsyncMock())
        empty=MagicMock();empty.scalars.return_value.first.return_value=None
        db.execute.return_value=empty
        with patch('app.services.cad.enclosure_cad_generator.EnclosureCadGeneratorService.calculate_enclosure_specs',side_effect=ValueError('Missing dimensions')),patch('app.services.export.quotation_exporter.QuotationExporterService.export',return_value='nonexistent-qa-file.xlsx'):
            result=asyncio.run(Pipeline.generate_cad_and_quotation(project=SimpleNamespace(id=0,name='QA'),db=db,devices=[device().model_dump()]))
        self.assertTrue(result['quotation_rows'])
        self.assertIsNone(result['cad_file'])
        self.assertIsNone(result['busbar_calc'])
        self.assertEqual(result['enclosure_spec']['sizing_status'],'needs_review')
    def test_bare_json_key_does_not_drop_later_devices(self):
        response='{"panels":[{"devices":[{"category":"LIGHT","name":"Đèn R","spec":""},{"category":"FUSE","name":"Cầu chì",_spec:"1x6A"},{"category":"MCB","name":"CB nhánh","spec":"2P16A6kA"}]}]}'
        rows=Parser.parse_device_list(response)
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[1].spec,'1x6A')

    def test_fuse_function_does_not_fabricate_lamp_and_box(self):
        response=json.dumps({'devices':[{'category':'FUSE','name':'Cầu chì đèn báo pha','spec':'1x6A','box_2d':[100,200,300,400]}]})
        rows=Parser.parse_device_list(response)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0].box_2d,[100,200,300,400])

    def test_one_phase_indicator_does_not_expand_fuse(self):
        rows=[device(),Device(category='LIGHT',name='Đèn báo pha R',spec='',panel_code='P')]
        Pipeline._infer_practical_quantities(rows)
        self.assertEqual(rows[0].quantity,1)

    def test_local_fuse_multiplicity_and_idempotence(self):
        rows=[Device(category='FUSE',name='Cầu chì',spec='3x6A',quantity=1)]
        Pipeline._infer_practical_quantities(rows);Pipeline._infer_practical_quantities(rows)
        self.assertEqual(rows[0].quantity,3)

    def test_duplicate_box_does_not_sum_and_distinct_tags_are_kept(self):
        rows=[device(box_2d=[100,100,200,200]),device(box_2d=[100,100,200,200])]
        self.assertEqual(len(normalize_takeoff(rows)[0]),1)
        rows[0].tag='FU1';rows[1].tag='FU2'
        self.assertEqual(len(normalize_takeoff(rows)[0]),2)

    def test_recorded_facade_result_corrects_eleven_to_eight(self):
        path=Path(__file__).parent/'fixtures/facade_takeoff.json'
        rows=[Device(**d) for d in json.loads(path.read_text(encoding='utf-8'))]
        Pipeline._infer_practical_quantities(rows)
        rows,warnings=normalize_takeoff(rows)
        self.assertEqual(sum(d.quantity for d in rows),8)
        self.assertEqual(len([d for d in rows if d.category=='LIGHT']),1)
        self.assertTrue(warnings)

    def test_missing_prices_and_assembly_do_not_become_zero_quotes(self):
        rows=build_quotation_rows([device()],{},None)
        items=[r for r in rows if r['row_type'] in ['item','accessory']]
        self.assertTrue(all(r['unit_price'] is None and r['line_total'] is None for r in items))
        self.assertFalse(any('sứ' in r['name'].lower() for r in items))
        self.assertTrue(any(r['quantity'] is None for r in items))

    def test_lighting_contactor_does_not_require_motor_overload(self):
        rows=[Device(category='CONTACTOR',name='K',spec='2P40A',connected_load='Chiếu sáng facade',source_filename='source.jpg')]
        titles=[r['title'] for r in technical_audit(rows)['missing_items']]
        self.assertNotIn('Kiểm tra bảo vệ quá tải của cụm contactor',titles)

    def test_catalogtb_references_never_claim_price_or_sku(self):
        engine=DeviceCatalogEngine.get_instance()
        self.assertTrue(engine.reference_profiles)
        self.assertTrue(all(p['sku'] is None and p['price'] is None for p in engine.reference_profiles))
        self.assertFalse(engine.lookup_device_info(category='MCB',part_number='UNKNOWN')['catalog_matched'])
        self.assertTrue(engine.search_references('MCCB','LS',3))

if __name__=='__main__':unittest.main()

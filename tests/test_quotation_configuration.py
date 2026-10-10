import unittest
from app.services.ai.quotation_configuration import apply_configuration, category, panel_key, schematic_devices


class QuotationConfigurationTests(unittest.TestCase):
    def fixture(self):
        source = [{'category':'CONTACTOR','name':'Pump','spec':'2P 16A','poles':2,'in_a':16,
                   'quantity':3,'panel_code':'TĐ-PX1','tag':'C1','source_filename':'sld.pdf'}]
        quote = {'source_filename':'quote.xlsx','items':[
            {'category':'CONTACTOR','panel_code':'PX1','original_text':'Contactor 2P 16A => 20A',
             'poles':2,'current_a':20,'quantity':3,'model':'NCH8-20','brand':'Chint','row':31,'evidence':'Code!31'},
            {'category':'SELECTOR_3_POSITION','panel_code':'PX1','original_text':'Công tắc 3 vị trí',
             'quantity':3,'brand':'Morele','row':34,'evidence':'Code!34'}]}
        return source,quote

    def test_revision_retains_source_and_adds_controls_once(self):
        source,quote=self.fixture()
        rows=apply_configuration(source,quote)
        self.assertEqual(sum(d['quantity'] for d in rows),6)
        self.assertEqual(rows[0]['in_a'],20)
        self.assertEqual(rows[0]['original_spec'],'2P 16A')
        self.assertEqual(rows[0]['source_observations']['schematic']['device']['in_a'],16)
        self.assertEqual(rows[0]['part_number'],'NCH8-20')
        self.assertEqual(rows[1]['mounting_face'],'inner_door')
        self.assertEqual(apply_configuration(rows,quote),rows)

    def test_unmatched_source_or_quote_cannot_disappear(self):
        source,quote=self.fixture()
        source[0]['quantity']=4
        with self.assertRaisesRegex(ValueError,'chưa có trong báo giá'): apply_configuration(source,quote)
        source[0]['quantity']=2
        with self.assertRaisesRegex(ValueError,'chưa ghép'): apply_configuration(source,quote)

    def test_rerun_recovers_schematic_without_quote_only_controls(self):
        source,quote=self.fixture()
        rows=apply_configuration(source,quote)
        recovered=schematic_devices(rows)
        self.assertEqual(recovered,source)
        self.assertEqual(sum(d['quantity'] for d in recovered),3)
        recovered[0]['in_a']=999
        self.assertEqual(rows[0]['source_observations']['schematic']['device']['in_a'],16)
        self.assertEqual(source[0]['in_a'],16)

    def test_panel_scope_and_accessories(self):
        self.assertEqual(panel_key('TĐ-PX1'),panel_key('PX1'))
        self.assertEqual(category('Role trung gian'),'RELAY')
        self.assertEqual(category('Bộ nguồn 24VDC'),'POWER_SUPPLY')
        self.assertIsNone(category('Cáp lực + thanh lược đồng'))

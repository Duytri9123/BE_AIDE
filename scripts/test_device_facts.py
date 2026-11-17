import unittest
from app.services.ai.device_facts import enrich_device_facts, enrich_quotation_facts


class DeviceFactsTests(unittest.TestCase):
    def test_explicit_aliases_backfill(self):
        result=enrich_device_facts({'category':'MCCB','detected_brand':'LS','model':'ABN103c'})
        self.assertEqual((result['brand'],result['part_number']),('LS','ABN103c'))
        self.assertFalse(result['installation_review']['auto_cutout_allowed'])

    def test_suggestions_do_not_become_identity(self):
        result=enrich_device_facts({'category':'MCCB','suggested_brands':['LS'],'catalog_candidates':{'LS':[{'sku':'X'}]},'tag':'QF1'})
        self.assertNotIn('brand',result)
        self.assertNotIn('part_number',result)

    def test_conflict_not_guessed_and_selection_preserved(self):
        result=enrich_device_facts({'category':'MCCB','manufacturer':'ABB','detected_brand':'LS'})
        self.assertNotIn('brand',result)
        self.assertEqual(result['identity_review']['brand']['status'],'conflicting_source_fields')
        self.assertEqual(enrich_device_facts({'brand':'ABB','detected_brand':'LS'})['brand'],'ABB')

    def test_quote_linked_by_panel_and_tag_only(self):
        rows=[{'id':'panel-A','row_type':'panel_header','panel_code':'A'},
            {'row_type':'item','category':'CONTACTOR','source_tags':['KM1'],'origin':'','sku':'','unit_price':100,'line_total':100,'quantity':1}]
        devices=[{'panel_code':'A','tag':'KM1','brand':'LS','part_number':'MC-9b'},
            {'panel_code':'B','tag':'KM1','brand':'ABB','part_number':'B'}]
        row=enrich_quotation_facts(rows,devices)[1]
        self.assertEqual((row['origin'],row['sku']),('LS','MC-9b'))
        self.assertEqual((row['unit_price'],row['line_total'],row['quantity']),(100,100,1))
        self.assertEqual(enrich_quotation_facts([{**rows[1],'source_tags':[]}],devices)[0]['sku'],'')

    def test_packages_not_given_fake_models(self):
        result=enrich_device_facts({'commercial_package':True,'row_type':'item','name':'Nhân công'})
        self.assertFalse(result['identity_required'])
        self.assertEqual(result['identity_review']['part_number']['status'],'not_applicable')

    def test_known_manufacturer_not_named_asian(self):
        from app.services.export.quotation_names import quotation_name
        self.assertEqual(quotation_name({'category':'PUSHBUTTON','name':'Nút START','brand':'CHINT'}),'Nút START')

    def test_only_matched_price_identity_can_fill(self):
        candidate={'brand':'LS','sku':'MC-9b','price':100}
        result=enrich_device_facts({'category':'CONTACTOR','pricebook_match':{'status':'matched','row':candidate}})
        self.assertEqual((result['brand'],result['part_number']),('LS','MC-9b'))
        unresolved=enrich_device_facts({'category':'CONTACTOR','pricebook_match':{'status':'ambiguous','row':candidate}})
        self.assertNotIn('brand',unresolved)

    def test_schema_preserves_installation_observation(self):
        from app.schemas.ai import ExtractedDeviceSchema
        obj=ExtractedDeviceSchema.model_validate(enrich_device_facts({'category':'PUSHBUTTON','name':'START','spec':'NO',
            'installation_observation':{'cutout_required':True,'source_reference':'drawing p1'}}))
        self.assertTrue(obj.installation_observation['cutout_required'])
        self.assertFalse(obj.installation_review['auto_cutout_allowed'])

    def test_quotation_builder_uses_explicit_facts(self):
        from app.services.ai.procurement_review import build_quotation_rows
        rows=build_quotation_rows([{'panel_code':'A','category':'CONTACTOR','tag':'KM1','name':'Contactor','spec':'9A',
            'detected_brand':'LS','part_number':'MC-9b','quantity':1}],{},refresh_prices=False)
        row=next(row for row in rows if row.get('source_tags')==['KM1'])
        self.assertEqual(row['origin'],'LS')
        self.assertIsNone(row['unit_price'])


if __name__=='__main__':unittest.main()

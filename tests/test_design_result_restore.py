import unittest
from uuid import uuid4
from app.services.ai.analysis_result import _build_analysis_result_schema


class DesignResultRestoreTests(unittest.TestCase):
    def test_pending_panels_and_blockers_survive_reload(self):
        result = _build_analysis_result_schema(uuid4(), 1, [], {
            'design_result': {'cad_status':'needs_review', 'cad_blockers':['PX2: missing geometry']},
            'enclosure_spec': {'sizing_status':'needs_review'},
            'panel_designs': {'PX1': {'cad_status':'ready'}, 'PX2': {'cad_status':'needs_review'}}})
        self.assertEqual(result.cad_status, 'needs_review')
        self.assertEqual(result.cad_blockers, ['PX2: missing geometry'])
        self.assertEqual([p['panel_code'] for p in result.panel_designs], ['PX1', 'PX2'])

    def test_ready_design_and_quote_rows_survive_reload(self):
        result = _build_analysis_result_schema(uuid4(), 1, [], {
            'design_result': {'cad_status':'ready', 'cad_blockers':[]},
            'enclosure_spec': {'height':700},
            'quotation_rows':[{'name':'Q1','quantity':1}],
            'cad_layout': {'release_ready':True}}, cad_file_info={'id':1})
        self.assertEqual(result.cad_status, 'ready')
        self.assertEqual(result.cad_file['id'], 1)
        self.assertEqual(len(result.quotation_rows), 1)
        self.assertTrue(result.cad_layout['release_ready'])

    def test_quotation_design_does_not_replace_source_takeoff_or_restore_old_cad(self):
        source=[{'category':'MCB','name':'Original','spec':'1P 16A','quantity':1}]
        result=_build_analysis_result_schema(uuid4(),1,source,{
            'source_configuration':'quotation',
            'design_devices':[{'category':'MCB','name':'Approved','spec':'1P 20A','quantity':1}],
            'design_result':{'cad_status':'needs_review','cad_file':None}},cad_file_info={'id':999})
        self.assertEqual(result.source_configuration,'quotation')
        self.assertEqual(result.devices[0].name,'Approved')
        self.assertIsNone(result.cad_file)
        self.assertEqual(source[0]['name'],'Original')

import unittest,uuid
from unittest.mock import patch
from app.services.ai.analysis_result import _build_analysis_result_schema

class SavedTakeoffReadTests(unittest.TestCase):
    def test_opening_saved_takeoff_does_not_start_cad_sizing(self):
        rows=[{'category':'LIGHT','name':'Đèn pha','spec':'','quantity':3,'panel_code':'P','evidence_image':'source'}]
        with patch('app.services.cad.enclosure_cad_generator.EnclosureCadGeneratorService.calculate_enclosure_specs',side_effect=AssertionError('Unexpected CAD sizing')):
            result=_build_analysis_result_schema(uuid.uuid4(),1,rows,{'technical_audit':{'cluster_review':[]}},iteration_id=88)
        self.assertEqual(result.enclosure_spec['status'],'pending_design')
        self.assertEqual(result.devices[0].evidence_image,'source')
        self.assertEqual(result.devices[0].quantity,3)

    def test_existing_design_dimensions_are_kept(self):
        result=_build_analysis_result_schema(uuid.uuid4(),1,[],{'enclosure_spec':{'height':1000,'width':600,'depth':300}})
        self.assertEqual(result.enclosure_spec['height'],1000)

if __name__=='__main__':unittest.main()

import copy
import unittest
from unittest.mock import patch, AsyncMock, MagicMock
from app.schemas.ai import ExtractedDeviceSchema
from app.services.ai.panel_identity import normalize_panel_identities, panel_identity
from app.services.ai.session_catalog_chat import catalog_request_brand, lookup_session_catalog

class SessionFollowupTests(unittest.IsolatedAsyncioTestCase):
    def test_panel_aliases_preserve_all_devices_and_distinct_numbers(self):
        panels=[{'panel_code':'TĐT'},{'panel_code':'TĐ-BTA'},{'panel_code':'TDT'}]
        devices=[ExtractedDeviceSchema(category='FUSE',name='Fuse',spec='',panel_code='TDT',quantity=3),
                 ExtractedDeviceSchema(category='MCB',name='CB',spec='',panel_code='TĐT',quantity=1),
                 ExtractedDeviceSchema(category='MCB',name='Pump',spec='',panel_code='TĐ-BTA',quantity=1)]
        normalize_panel_identities(devices,panels)
        self.assertEqual([d.panel_code for d in devices],['TĐT','TĐT','TĐ-BTA'])
        self.assertEqual(sum(d.quantity for d in devices),5)
        self.assertNotEqual(panel_identity('T1.1'),panel_identity('T11'))

    def test_horizontal_rows_are_measured_from_source_labels(self):
        from PIL import Image
        from app.services.ai.row_evidence import horizontal_feeder_boxes
        def anchor(text,l,t,r,b):return {'text':text,'confidence':.99,'polygon':[[l,t],[r,t],[r,b],[l,b]]}
        ocr=[anchor('L5/b',100,100,140,120),anchor('L6/r',100,180,140,200),anchor('L7',100,260,140,280),
             anchor('CB-2P',200,100,280,120),anchor('CB-2P',200,180,280,200),anchor('CB-3P',200,260,280,280)]
        devices=[ExtractedDeviceSchema(category='MCB',name='L5',tag='L5',spec='30A')]
        result=horizontal_feeder_boxes(Image.new('RGB',(1000,1000)),devices,ocr)['boxes']
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['observed_tag'],'L5/b')
        box=result[0]['symbol_box_2d']
        self.assertLessEqual(box[0],100)
        self.assertGreaterEqual(box[3],280)
        self.assertLess(box[2],180)

    def test_search_intent_does_not_capture_edits(self):
        self.assertEqual(catalog_request_brand('tìm kiếm cho tôi hãng ls nhé'),'LS Electric')
        self.assertEqual(catalog_request_brand('đối chiếu catalog Schneider'),'Schneider')
        self.assertIsNone(catalog_request_brand('đổi hãng sang LS'))
        self.assertIsNone(catalog_request_brand('xóa MCB LS'))

    async def test_search_reuses_snapshot_without_changing_source_or_auxiliaries(self):
        devices=[{'category':'MCB','name':'L1','tag':'L1','quantity':1,'spec':'3P 20A 6kA','brand':'','evidence_image':'source'},
                 {'category':'LIGHT','name':'Đèn R','quantity':1,'spec':'','brand':''}]
        before=copy.deepcopy(devices)
        candidates={'LS Electric':[{'sku':'LS-code','rating_complete':True}], 'CHINT':[{'sku':'other'}]}
        with patch('app.services.device_catalog_engine.DeviceCatalogEngine.get_instance',return_value=MagicMock()), \
             patch('app.services.ai.device_recommendations.recommendations',return_value=candidates), \
             patch('app.services.ai.web_device_recommendations.research_device_products',new_callable=AsyncMock) as research:
            edited,reply=await lookup_session_catalog(devices,'LS Electric',[],None)
        self.assertEqual(devices,before)
        self.assertEqual(edited[1],devices[1])
        for field in ('quantity','spec','brand','evidence_image','tag'):
            self.assertEqual(edited[0][field],devices[0][field])
        self.assertEqual(list(edited[0]['catalog_candidates']),['LS Electric'])
        self.assertIn('1 dòng thiết bị chính',reply)
        research.assert_awaited_once()

if __name__=='__main__':unittest.main()

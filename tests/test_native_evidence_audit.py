import unittest
from unittest.mock import AsyncMock,patch
from PIL import Image
from app.schemas.ai import ExtractedDeviceSchema
from app.services.ai.source_image_evidence import audit_crops,retry_unverified_evidence
from app.services.ai.ocr_source_evidence import grounded_boxes, supplement_selectors


class NativeEvidenceAuditTests(unittest.IsolatedAsyncioTestCase):
    def device(self):
        return ExtractedDeviceSchema(category='MCB',name='CB nhánh',spec='3P 10A 6kA',tag='M1',quantity=1,in_a=10,poles=3,icu_ka=6)

    def payload(self):
        return {'boxes':[{'device_id':'0','verified':True,'symbol_box_2d':[50,100,200,300],
                         'text_box_2d':[50,310,200,500],'tag_box_2d':[500,100,530,150]}]}

    async def test_failed_actual_crop_cannot_change_source_parameters(self):
        device=self.device()
        call=AsyncMock(return_value='{"checks":[{"device_id":"0","matches":false,"observed":"wrong branch","in_a":16}]}')
        output=await audit_crops(Image.new('RGB',(900,1600),'white'),call,[device],self.payload())
        self.assertFalse(output['boxes'][0]['verified'])
        self.assertEqual(10,device.in_a)

    async def test_main_breaker_text_outside_branch_region_cannot_override_rating(self):
        device=self.device()
        payload=self.payload()
        payload['boxes'][0]['source_region']=[260,80,350,550]
        call=AsyncMock(return_value='{"checks":[{"device_id":"0","matches":true,"observed":"63A 18kA","in_a":63,"icu_ka":18}]}')
        output=await audit_crops(Image.new('RGB',(900,1600),'white'),call,[device],payload)
        self.assertFalse(output['boxes'][0]['verified'])
        self.assertEqual(10,device.in_a)
        call.assert_not_called()

    async def test_ratings_are_reread_from_confirmed_crop(self):
        device=self.device()
        call=AsyncMock(return_value='{"checks":[{"device_id":"0","matches":true,"observed":"M1 MCB 2P 16A 6kA", "source_spec":"2P 16A 6kA", "poles":2,"in_a":16,"icu_ka":6}]}')
        output=await audit_crops(Image.new('RGB',(900,1600),'white'),call,[device],self.payload())
        self.assertTrue(output['boxes'][0]['verified'])
        self.assertEqual((2,16,'2P 16A 6kA'),(device.poles,device.in_a,device.spec))

    async def test_explicit_breaker_label_corrects_prior_type_reading(self):
        device=self.device()
        call=AsyncMock(return_value='{"checks":[{"device_id":"0","matches":true,"observed":"M1 MCCB 3P 10A 6kA","source_category":"MCCB","source_spec":"3P 10A 6kA"}]}')
        await audit_crops(Image.new('RGB',(900,1600),'white'),call,[device],self.payload())
        self.assertEqual('MCCB',device.category)

    async def test_missing_visual_audit_is_not_success(self):
        output=await audit_crops(Image.new('RGB',(900,1600),'white'),AsyncMock(return_value='{"checks":[]}'),[self.device()],self.payload())
        self.assertFalse(output['boxes'][0]['verified'])

    async def test_targeted_retry_preserves_confirmed_rows_and_global_identity(self):
        confirmed={'device_id':'0','verified':True,'symbol_box_2d':[1,2,3,4]}
        pending={'device_id':'1','verified':False}
        with patch('app.services.ai.source_image_evidence.refine_locations',AsyncMock(return_value={'boxes':[{'device_id':'0','verified':True}]})) as refine, \
             patch('app.services.ai.source_image_evidence.audit_crops',AsyncMock(return_value={'boxes':[{'device_id':'0','verified':True,'symbol_box_2d':[10,20,30,40]}]})):
            output=await retry_unverified_evidence(Image.new('RGB',(900,1600),'white'),AsyncMock(),[self.device(),self.device()],{'boxes':[confirmed,pending]})
        self.assertEqual(confirmed,output['boxes'][0])
        self.assertEqual('1',output['boxes'][1]['device_id'])
        self.assertEqual(1,len(refine.call_args.args[2]))

    def test_no_measured_tag_means_no_invented_branch_crop(self):
        image=Image.new('RGB',(900,1600),'white')
        output=grounded_boxes(image,[self.device()],[],[],[])
        self.assertEqual([],output['boxes'])

    async def test_count_alone_cannot_create_a_missing_selector(self):
        devices=[self.device()]
        counts={'counts':[{'panel_code':'P','category':'MCB','quantity':1},
                          {'panel_code':'P','category':'SELECTOR','quantity':1}]}
        call=AsyncMock(return_value='{"symbol_present":false}')
        markers=[{'text':'AS','circle':[60,60,6],'box':[62,45,80,56]}]
        result=await supplement_selectors(Image.new('RGB',(900,1600),'white'),call,devices,counts,markers)
        self.assertEqual(1,len(result))

    async def test_local_visual_proof_resolves_omitted_source_symbol(self):
        devices=[self.device()]
        counts={'counts':[{'panel_code':'P','category':'MCB','quantity':1},
                          {'panel_code':'P','category':'SELECTOR','quantity':1}]}
        call=AsyncMock(return_value='{"symbol_present":true,"category":"SELECTOR","observed_tag":"AS","name":"Chuyển mạch ampe","spec":""}')
        markers=[{'text':'AS','circle':[60,60,6],'box':[62,45,80,56]}]
        result=await supplement_selectors(Image.new('RGB',(900,1600),'white'),call,devices,counts,markers)
        self.assertEqual(('SELECTOR','AS','P'),(result[-1].category,result[-1].tag,result[-1].panel_code))


if __name__=='__main__':
    unittest.main()

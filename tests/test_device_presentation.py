import base64,io,unittest
from PIL import Image
from app.services.ai.evidence_preview import device_preview
from app.services.ai.circuit_context import enrich_circuit_context
from app.services.export.dynamic_grouping import DynamicGroupingEngine


class DevicePresentationTests(unittest.TestCase):
    def test_distant_source_parts_are_separate_images_without_fake_canvas(self):
        image=Image.new('RGB',(1000,1000),'white')
        image.paste('black',(100,100,160,160));image.paste('blue',(800,800,900,850))
        previews=device_preview(image,{'symbol_box_2d':[100,100,160,160],'text_box_2d':[800,800,850,900]},tight=True)
        self.assertEqual(len(previews),2)
        crops=[Image.open(io.BytesIO(base64.b64decode(p['evidence_image'].split(',')[1]))) for p in previews]
        self.assertLess(crops[0].height,100);self.assertLess(crops[1].height,100)
        self.assertEqual(crops[0].getpixel((10,10)),(0,0,0))
        self.assertEqual(crops[1].getpixel((10,10)),(0,0,255))

    def test_horizontal_symbol_keeps_nearby_rating_with_distant_tag_separate(self):
        image=Image.new('RGB',(1000,1000),'white')
        image.paste('red',(190,415,265,425))  # rating above the horizontal contact
        image.paste('black',(202,425,212,439))
        image.paste('blue',(394,419,406,429))  # distant tag
        previews=device_preview(image,{'symbol_box_2d':[425,202,439,212],
            'text_box_2d':[415,184,425,265],'tag_box_2d':[419,394,429,406]},tight=True)
        self.assertEqual(len(previews),2)
        first=Image.open(io.BytesIO(base64.b64decode(previews[0]['evidence_image'].split(',')[1]))).convert('RGB')
        colors={color for _,color in first.getcolors(first.width*first.height)}
        self.assertIn((255,0,0),colors);self.assertIn((0,0,0),colors)
        self.assertNotIn((0,0,255),colors)
        self.assertLess(first.width,100);self.assertLess(first.height,40)
        self.assertEqual(previews[1]['label'],'Ký hiệu lộ')

    def test_branch_identity_is_not_device_type_or_meter_function(self):
        from app.services.ai.scoped_takeoff import ground_scoped_identity
        source=[{'text':'P4. BẾP HỒNG NGOẠI'}]
        device=ground_scoped_identity({'category':'RCBO','tag':'RCBO','connected_load':'P4. BẾP HỒNG NGOẠI'},source)
        self.assertEqual(device['tag'],'P4')
        self.assertEqual(device['connected_load'],'P4. BẾP HỒNG NGOẠI')
        meter=ground_scoped_identity({'category':'METER','tag':'V','connected_load':'Hiển thị điện áp'},source)
        self.assertIsNone(meter['tag']);self.assertIsNone(meter['connected_load'])
        self.assertEqual(meter['electrical_function'],'Hiển thị điện áp')
        # No CAD transcript is not proof that a load label is absent on an image/PDF.
        image=ground_scoped_identity({'category':'METER','tag':'M1','connected_load':'Machine A'},[])
        self.assertEqual(image['connected_load'],'Machine A')

    def test_context_uses_the_exact_row_and_explicit_power_unit(self):
        labels=[{'id':'tag','text':'L4','x':30,'y':100,'height':10},
                {'id':'rating','text':'MCB-1P-10A-6kA','x':10,'y':100,'height':10},
                {'id':'cable','text':'CU/PVC 1.5MM2 - ĐI TRÊN TRẦN','x':50,'y':100,'height':10},
                {'id':'power','text':'0.8','x':200,'y':100,'height':10},
                {'id':'load','text':'CHIẾU SÁNG','x':300,'y':100,'height':10},
                {'id':'header','text':'CÔNG SUẤT (kW)','x':200,'y':300,'height':10}]
        row={'tag':'L4','spec':'MCB-1P-10A-6kA','connected_load':'CHIẾU SÁNG'}
        evidence={'labels':labels,'rows':[{'id':'tag','rating_id':'rating','tag':'L4','rating':'MCB-1P-10A-6kA'}]}
        enrich_circuit_context([row],evidence)
        self.assertEqual(row['circuit_context']['power_w'],800)
        self.assertEqual(row['circuit_context']['cable_spec'],'CU/PVC 1.5MM2')
        self.assertEqual(row['circuit_context']['installation_method'],'ĐI TRÊN TRẦN')
        labels[-1]['text']='CÔNG SUẤT'
        other={'tag':'L4','spec':'MCB-1P-10A-6kA','connected_load':'CHIẾU SÁNG'}
        enrich_circuit_context([other],evidence)
        self.assertNotIn('power_w',other['circuit_context'])

    def test_quotation_combines_identical_devices_without_mixing_units_or_prices(self):
        first={'category':'MCB','name':'MCB (Lộ L1)','spec':'1P-10A-6kA','panel_code':'P1','unit':'Cái','quantity':1,'unit_price':100,'tag':'L1'}
        second={**first,'name':'Aptomat tép (Lộ L2)','quantity':2,'tag':'L2'}
        result=DynamicGroupingEngine.merge_duplicates([first,second])
        self.assertEqual(len(result),1);self.assertEqual(result[0]['quantity'],3)
        self.assertEqual(result[0]['source_tags'],['L1','L2'])
        for change in ({'unit':'Bộ'},{'unit_price':200},{'panel_code':'P2'},{'spec':'1P-16A-6kA'}):
            self.assertEqual(len(DynamicGroupingEngine.merge_duplicates([first,{**second,**change}])),2)
        self.assertEqual(len(DynamicGroupingEngine.merge_duplicates([{**first,'unit_price':None},{**second,'unit_price':0}])),2)
        self.assertEqual(DynamicGroupingEngine.merge_duplicates([{**first,'quantity':0},{**second,'quantity':0}])[0]['quantity'],0)

class CropAuditReadabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_audit_keeps_source_parts_readable(self):
        from types import SimpleNamespace
        from app.services.ai.device_crop_audit import audit_device_previews
        source=Image.new('RGB',(1000,1000),'white')
        source.paste('red',(100,100,200,200))
        row={'device_id':'0','verified':True,'symbol_verified':True,
             'symbol_box_2d':[100,100,200,200],'text_box_2d':[300,400,400,500],
             'tag_box_2d':[700,800,800,900],'load_box_2d':[850,100,900,200],
             'load_verified':True,'relationship_evidence':'source wire','load_label':'LOAD'}
        device=SimpleNamespace(name='MCB',tag='P1',spec='20A',quantity=1,unit='Cái',connected_load='LOAD')
        async def call(path,prompt):
            import json
            with Image.open(path) as sheet:
                red_y=[]
                for y in range(sheet.height):
                    if any(sheet.getpixel((x,y))[:3]==(255,0,0) for x in range(0,500,4)):red_y.append(y)
                from itertools import groupby
                longest=max(len(list(g)) for _,g in groupby(enumerate(red_y),key=lambda item:item[0]-item[1]))
                self.assertGreater(longest,100)
            return json.dumps({'checks':[{'device_id':'0','matches':True,'symbol_complete':True,
                'label_complete':True,'isolated':True,'tag_matches':True,'load_matches':True,'relationship_verified':True}]})
        result=await audit_device_previews(source,call,[device],{'boxes':[row]})
        self.assertTrue(result['boxes'][0]['verified'])

if __name__=='__main__':unittest.main()

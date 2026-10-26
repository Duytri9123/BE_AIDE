import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image,ImageDraw
from app.schemas.ai import ExtractedDeviceSchema as Device
from app.services.ai.evidence_geometry import refine_dense_measurement,refine_spare_symbol

class EvidenceGeometryTests(unittest.TestCase):
    def test_separates_meter_selector_and_lamp_without_changing_inventory(self):
        meter=Device(category='VOLTMETER',name='Meter',spec='0-600V',quantity=1,box_2d=[500,400,600,500])
        lamp=Device(category='LIGHT',name='R Y B',spec='0-600V',quantity=3,box_2d=[470,380,520,500])
        selector=Device(category='SELECTOR',name='Selector',spec='',quantity=1)
        circles=np.array([[[250,180,20],[330,180,8]]],dtype=np.float32)
        with patch('app.services.ai.evidence_geometry.cv2.HoughCircles',return_value=circles):
            refine_dense_measurement(Image.new('RGB',(1000,1000),'white'),[meter,lamp,selector])
        self.assertLess(lamp.box_2d[2],meter.box_2d[0])
        self.assertEqual(lamp.spec,'')
        self.assertEqual([d.quantity for d in (meter,lamp,selector)],[1,3,1])
        self.assertLess(meter.evidence_region['symbol_box_2d'][3],selector.box_2d[1])
        self.assertEqual(selector.evidence_region['coordinate_basis'],'measured_source_circle_next_to_meter')

    def test_meter_preview_does_not_include_ink_outside_its_measured_outline(self):
        import base64,io
        from app.services.ai.analysis_pipeline_service import AnalysisPipelineService as Pipeline
        image=Image.new('RGB',(100,100),'white');draw=ImageDraw.Draw(image)
        draw.rectangle((20,30,70,42),fill='black')
        draw.ellipse((35,45,65,75),outline='black',width=3)
        draw.line((50,55,50,65),fill='black',width=3)
        meter=Device(category='VOLTMETER',name='Meter',spec='0-600V',box_2d=[300,300,800,700],evidence_region={
            'symbol_box_2d':[300,300,800,700],'text_box_2d':[300,200,420,700],
            'symbol_circle':[500,600,150,150]})
        details=Pipeline._linked_evidence_images(meter,image)
        cropped=Image.open(io.BytesIO(base64.b64decode(details[0]['evidence_image'].split(',',1)[1])))
        left,top,_,_=Pipeline._evidence_crop_pixels(meter.evidence_region['symbol_box_2d'],100,100)
        self.assertEqual(cropped.getpixel((50-left,35-top)),(255,255,255))
        self.assertEqual(cropped.getpixel((50-left,60-top)),(0,0,0))

    def test_no_pixel_match_does_not_create_a_selector_crop(self):
        meter=Device(category='VOLTMETER',name='Meter',spec='',box_2d=[500,400,600,500])
        selector=Device(category='SELECTOR',name='Selector',spec='')
        with patch('app.services.ai.evidence_geometry.cv2.HoughCircles',return_value=None):
            refine_dense_measurement(Image.new('RGB',(1000,1000)),[meter,selector])
        self.assertIsNone(selector.box_2d)

    def test_spare_crop_contains_both_cross_and_switch_arm_excluding_distant_load_label(self):
        image=Image.new('RGB',(1000,1000),'white');draw=ImageDraw.Draw(image)
        draw.line((100,515,120,535),fill='black',width=3)
        draw.line((100,535,120,515),fill='black',width=3)
        draw.line((125,500,200,525),fill='black',width=4)
        draw.line((200,525,700,525),fill='black',width=3)
        spare=Device(category='CB',name='CB dự phòng',spec='',evidence_region={
            'box_2d':[490,100,540,800],'symbol_box_2d':[500,100,520,120],
            'text_box_2d':[510,700,540,800]})
        refine_spare_symbol(image,[spare])
        self.assertIsNotNone(spare.box_2d)
        self.assertLessEqual(spare.box_2d[1],100)
        self.assertGreaterEqual(spare.box_2d[3],200)
        self.assertLess(spare.box_2d[3],700)

if __name__=='__main__':unittest.main()

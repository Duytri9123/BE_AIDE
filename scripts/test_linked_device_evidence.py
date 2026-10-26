import unittest
import base64
import io
from PIL import Image
from app.schemas.ai import ExtractedDeviceSchema as Device
from app.services.ai.analysis_pipeline_service import AnalysisPipelineService as Pipeline


class LinkedEvidenceTests(unittest.TestCase):
    def test_slanted_branch_preserves_endpoints_and_masks_adjacent_rows(self):
        d = Device(category='CONTACTOR', name='C', spec='2P 16A',
            box_2d=[100,100,150,200], evidence_region={'load_verified':True,
            'load_box_2d':[250,700,300,900], 'relationship_evidence':'Verified wire connection'})
        result = next(row for row in Pipeline._linked_evidence_images(d, Image.new('RGB',(1000,1000),'white')) if row['kind']=='branch')
        crop = Image.open(io.BytesIO(base64.b64decode(result['evidence_image'].split(',',1)[1])))
        self.assertEqual(crop.mode, 'RGB')
        self.assertGreater(crop.width, 4 * crop.height)
        self.assertEqual(crop.getpixel((crop.width//2,crop.height//2)), (255,255,255))

    def test_branch_crops_only_target_row_without_neighbours(self):
        from PIL import ImageDraw
        im = Image.new('RGB', (1000, 1000), 'white')
        draw = ImageDraw.Draw(im)
        draw.rectangle((300,190,780,205), fill='red')
        draw.rectangle((300,215,780,233), fill='black')
        draw.rectangle((300,245,780,260), fill='blue')
        device = Device(category='MCB', name='L4', spec='3P 20A', box_2d=[215,321,233,403],
            evidence_region={'load_verified':True,'load_box_2d':[220,703,228,764],
                             'relationship_evidence':'L4 connects to its load'})
        result = next(row for row in Pipeline._linked_evidence_images(device, im) if row['kind']=='branch')
        crop = Image.open(io.BytesIO(base64.b64decode(result['evidence_image'].split(',',1)[1])))
        self.assertLess(crop.height, 35)
        self.assertGreater(crop.width, 450)
        self.assertFalse(any(r > 120 and r > b * 2 and r > g * 2 for r,g,b in crop.get_flattened_data()))
        self.assertFalse(any(b > 120 and b > r * 2 and b > g * 2 for r,g,b in crop.get_flattened_data()))

    def test_load_is_not_claimed_without_verified_branch_connection(self):
        d = Device(category='CONTACTOR', name='C', spec='2P 16A', box_2d=[100,100,200,200])
        Pipeline._apply_verified_boxes([d], {'boxes': [{'device_id':0, 'verified':True,
            'box_2d':[100,100,200,200], 'load_verified':False, 'load_box_2d':[100,700,200,900]}]})
        self.assertEqual(Pipeline._linked_evidence_images(d, Image.new('RGB',(1000,1000))), [])

    def test_symbol_and_distant_load_are_two_distinct_crops(self):
        d = Device(category='CONTACTOR', name='C', spec='2P 16A')
        Pipeline._apply_verified_boxes([d], {'boxes': [{'device_id':0, 'verified':True,
            'box_2d':[100,100,200,200], 'load_verified':True, 'load_box_2d':[100,700,150,950],
            'load_label':'BƠM 02', 'relationship_evidence':'Nhánh P2 nối tới BƠM 02.'}]})
        images = Pipeline._linked_evidence_images(d, Image.new('RGB',(1000,1000)))
        self.assertEqual([image['kind'] for image in images], ['device','load','branch'])
        self.assertNotEqual(images[0]['evidence_image'], images[1]['evidence_image'])
        self.assertIn('BƠM 02', images[1]['label'])

    def test_reverification_discards_old_load_association(self):
        d = Device(category='MCB',name='CB',spec='16A',evidence_region={'load_verified':True,
            'load_label':'old', 'relationship_evidence':'old','load_box_2d':[100,700,200,900]})
        Pipeline._apply_verified_boxes([d], {'boxes':[{'device_id':0,'verified':False}]})
        self.assertFalse(d.evidence_region.get('load_verified'))


if __name__ == '__main__': unittest.main()

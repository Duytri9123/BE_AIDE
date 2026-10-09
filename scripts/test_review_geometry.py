import json
import logging
import tempfile
import unittest
from pathlib import Path
import ezdxf
from ezdxf.math import Vec3
from app.services.cad.catalogtb_assets import candidates, resolve
from app.services.cad.device_envelope import placement_bounds
from app.services.cad.library_assets import insert_library_asset
from app.services.cad.output_status import output_status
from app.services.cad.review_form_fit import fit_vertical_review
from app.services.cad.reference_panel_layout import generate
from app.services.cad.source_project_generator import SourceProjectGenerator


class ReviewGeometryTests(unittest.TestCase):
    def test_rotated_body_anchor_preserves_source(self):
        asset = next(a for a in candidates('MCB',poles=2) if 'BKN' in a['name'])
        bounds = placement_bounds(resolve(asset['id']))
        for rotation in (0,90,270):
            with self.subTest(rotation=rotation):
                doc=ezdxf.new();space=doc.modelspace()
                w,h=insert_library_asset(space,asset['id'],100,200,rotation)
                ref=list(space)[0]
                corners=[ref.matrix44().transform(Vec3(x,y,0)) for x,y in ((bounds[0],bounds[1]),(bounds[0],bounds[3]),(bounds[2],bounds[1]),(bounds[2],bounds[3]))]
                self.assertAlmostEqual(min(p.x for p in corners),100)
                self.assertAlmostEqual(min(p.y for p in corners),200)
                self.assertAlmostEqual(w,36 if rotation==0 else 82)
                self.assertAlmostEqual(h,82 if rotation==0 else 36)
                source=ezdxf.readfile(resolve(asset['id'])['path'])
                self.assertEqual(len(doc.blocks[ref.dxf.name]),len(source.modelspace()))
                self.assertEqual(ref.dxf.xscale,1)

    def test_real_tdt_uses_complete_form_and_all_devices(self):
        devices=json.loads(Path(__file__).with_name('fixtures').joinpath('selected_tdt_review.json').read_text(encoding='utf8'))
        dimensions=fit_vertical_review(devices,(1000,600,300))
        self.assertEqual(dimensions,(1200,800,300))
        with tempfile.TemporaryDirectory() as out:
            result=generate(devices,dimensions,out)
            self.assertTrue(result['enclosure_source']['complete_source_sheet'])
            self.assertEqual(result['enclosure_source']['scale'],1)
            self.assertFalse(result['missing'])
            measured=result['spacing_review']['measurements']
            self.assertTrue(measured['side_policy_satisfied'])
            self.assertAlmostEqual(measured['main_to_branch_vertical_gap_mm'],50)
            self.assertGreaterEqual(measured['branch_bottom_mm'],160)
            self.assertTrue(all(abs(p['gap_mm']-40)<0.01 for p in measured['branch_to_busbar_edges']))
            main=next(p for p in measured['body_to_shell'] if p['tag']=='MCCB-3P')
            self.assertAlmostEqual(main['top_mm'],250)
            self.assertEqual({d['tag'] for d in devices},{p['tag'] for p in result['placements'] if p['asset_id']})
            for p in result['placements']:
                if p['zone']=='outer_door':self.assertEqual(p['source_face_label'],'1st DOOR VIEW')
            self.assertFalse(output_status(True,True,result)['success'])
            self.assertFalse(ezdxf.readfile(result['dxf']).audit().errors)

    def test_file_presence_does_not_hide_missing_devices_or_conflicts(self):
        self.assertFalse(output_status(None,True,{})['success'])
        self.assertFalse(output_status(True,None,{})['success'])
        self.assertFalse(output_status(True,True,{'unmatched_devices':['Q1']})['success'])
        self.assertFalse(output_status(True,True,{},['overlap'])['success'])
        self.assertFalse(output_status(True,True,{})['success'])
        self.assertFalse(output_status(True,True,{'placements':[{'tag':'Q1'}], 'release_ready':False})['success'])
        self.assertFalse(output_status(True,True,{'placements':[{'tag':'Q1'}]}, devices=[{'tag':'Q2'}])['success'])
        self.assertTrue(output_status(True,True,{'placements':[{'tag':'Q1'}]})['success'])

    def test_branch_panel_uses_original_form_and_json_mounting_region(self):
        asset=next(a for a in candidates('MCB',poles=3) if 'BKN' in a['name'])
        devices=[dict(category='MCB',name='BTA',tag='CB-BTA',poles=3,in_a=20,quantity=1,cad={'asset_id':asset['id']})]
        with tempfile.TemporaryDirectory() as out:
            result=SourceProjectGenerator.generate(0,out,(500,300,300),devices=devices)
            self.assertEqual(result['dimensions'],{'height':600,'width':400,'depth':300})
            self.assertEqual(len(result['placements']),1)
            self.assertFalse(result['unmatched_devices'])
            self.assertEqual(result['status'],'reference_layout_needs_review')
            self.assertFalse(ezdxf.readfile(result['path']).audit().errors)


if __name__=='__main__':
    logging.getLogger('ezdxf').setLevel(logging.ERROR)
    unittest.main()

import io
import unittest
from unittest.mock import patch
import ezdxf
from app.core.config import settings
from app.services.cad import reserved_space as reserve
from app.services.cad.enclosure_cad_generator import EnclosureCadGeneratorService as Sizing
from app.services.cad.source_project_generator import SourceProjectGenerator as Source
from app.services.cad.output_status import output_status


class ReservedSpaceTests(unittest.TestCase):
    def test_reserved_fraction_is_of_final_space_not_added_percentage(self):
        with patch.object(settings, 'ENCLOSURE_RESERVE_SPACE_PCT', 15):
            self.assertEqual(reserve.sizing_height(850), 1000)
            region, zone = reserve.allocate((40,40,440,640))
        self.assertEqual(region, (40,130,440,640))
        self.assertAlmostEqual(zone['reserved_area_mm2']/zone['usable_area_mm2'], .15)

    def test_sizing_grows_and_lists_missing_depth_instead_of_inventing_it(self):
        device=dict(category='MCB',name='Main',tag='Q0',in_a=40,poles=2,quantity=1)
        with patch.object(Sizing, '_get_device_dimension', return_value=(80,200,60)):
            with patch.object(settings, 'ENCLOSURE_RESERVE_SPACE_PCT', 0):
                base=Sizing.calculate_enclosure_specs([device])
            with patch.object(settings, 'ENCLOSURE_RESERVE_SPACE_PCT', 15):
                reserved=Sizing.calculate_enclosure_specs([device])
        self.assertGreater(reserved['height'], base['height'])
        self.assertEqual(reserved['reserve_space']['status'], 'planned_requires_cad_verification')
        self.assertEqual(reserved['device_dimension_evidence'][0]['height_mm'], 200)
        with patch.object(Sizing, '_get_device_dimension', return_value=(80,200,0)):
            with self.assertRaisesRegex(ValueError, 'Q0'):
                Sizing.calculate_enclosure_specs([device])

    def test_missing_dimensions_report_all_devices(self):
        with patch.object(Sizing, '_get_device_dimension', side_effect=ValueError('missing geometry')):
            with self.assertRaises(ValueError) as caught:
                Sizing.calculate_enclosure_specs([{'tag':'Q1'},{'tag':'Q2'}])
        self.assertIn('Q1', str(caught.exception)); self.assertIn('Q2', str(caught.exception))

    def test_sizing_counts_every_device_in_a_grouped_takeoff_row(self):
        main=dict(category='MCB',name='Main',tag='Q0',in_a=40,poles=2,quantity=1)
        branch=dict(category='MCB',name='Branch',tag='L1-L21',in_a=16,poles=1,quantity=21)
        with patch.object(Sizing, '_get_device_dimension', return_value=(80,200,60)):
            one=Sizing.calculate_enclosure_specs([main,{**branch,'quantity':1}])
            many=Sizing.calculate_enclosure_specs([main,branch])
        self.assertEqual(many['feeder_count'],21)
        self.assertGreater(many['height']*many['width'],one['height']*one['width'])

    def test_cad_reserves_space_and_refuses_previously_fitting_device(self):
        form=ezdxf.new(); form.units=4
        stream=io.StringIO(); form.write(stream)
        device_doc=ezdxf.new(); device_doc.units=4
        device_doc.modelspace().add_lwpolyline([(0,0),(100,0),(100,90),(0,90)],close=True)
        device={'category':'MCB','tag':'Q1','cad':{'asset_id':'test'}}
        with patch.object(Source, '_interior_region', return_value=(0,0,200,100)), \
             patch('app.services.cad.library_assets.requested_asset', return_value=(True,'test')), \
             patch('app.api.v1.endpoints.cad_library.download_layout') as download, \
             patch('app.services.cad.source_project_generator.ezdxf.readfile', return_value=device_doc), \
             patch('app.services.cad.library_assets.insert_library_asset'):
            download.return_value.path='unused'
            with patch.object(settings, 'ENCLOSURE_RESERVE_SPACE_PCT', 0):
                _, placements, _ = Source._place_devices(stream.getvalue(),[device],{'depth':300},{})
                self.assertEqual(len(placements),1)
            with patch.object(settings, 'ENCLOSURE_RESERVE_SPACE_PCT', 15):
                with self.assertRaisesRegex(ValueError, 'không vừa|không đủ chỗ'):
                    Source._place_devices(stream.getvalue(),[device],{'depth':300},{})

    def test_dxf_roundtrip_checks_actual_rectangle_and_overlap(self):
        doc=ezdxf.new(); _, zone=reserve.allocate((0,0,400,1000))
        reserve.draw(doc.modelspace(),zone)
        stream=io.StringIO();doc.write(stream)
        restored=ezdxf.read(io.StringIO(stream.getvalue()))
        safe=[dict(tag='Q1',x=0,y=200,width=100,height=100,mounting_face='mounting_plate')]
        result=reserve.from_dxf(restored,safe)
        self.assertEqual(result['status'],'verified_empty')
        self.assertEqual(result['reserved_area_mm2'],60000)
        with self.assertRaisesRegex(ValueError,'Q1'):
            reserve.from_dxf(restored,[{**safe[0],'y':100}])
        self.assertFalse(output_status(True,True,{'reserve_space':{'status':'not_verified'}})['success'])


if __name__ == '__main__': unittest.main()

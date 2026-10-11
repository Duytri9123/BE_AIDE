from unittest import TestCase
from app.services.cad.placement_clearances import usable_region,device_gap

class ClearanceTest(TestCase):
    def test_sheet_bounds_do_not_imply_mounting_margins(self):
        with self.assertRaises(ValueError):usable_region((0,0,600,900),{},'mounting_plate')
    def test_reviewed_asymmetric_margins_follow_entry_side(self):
        item={'placement_rules':{'mounting_plate':{'verified':True,'source_handles':['AB'],
            'left_mm':20,'bottom_mm':120,'right_mm':40,'top_mm':60}}}
        self.assertEqual(usable_region((0,0,600,900),item,'mounting_plate'),(20,120,560,840))
    def test_only_modular_horizontal_adjacency_has_default(self):
        self.assertEqual(device_gap({'category':'MCB'},'horizontal'),0)
        with self.assertRaises(ValueError):device_gap({'category':'MCB'},'vertical')
        with self.assertRaises(ValueError):device_gap({'category':'MCCB'},'horizontal')

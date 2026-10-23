import unittest
from app.schemas.ai import ExtractedDeviceSchema as Device
from app.services.ai.cad_inventory_review import merge_additions


class CadInventoryReviewTests(unittest.TestCase):
    def test_missing_instruments_require_actual_source_labels_and_keep_source_counts(self):
        source=[{'text':x} for x in ['3x2A','R','Y','B']]
        main=Device(category='MCCB',name='Main',spec='3P 150A 22kA',quantity=1,panel_code='MDB',tag='Q0')
        payload={'devices':[
            dict(category='FUSE',name='Fuse',spec='2A',quantity=3,panel_code='MDB',tag='FU',source_quotes=['3x2A']),
            dict(category='LIGHT',name='Lamps',spec='',quantity=3,panel_code='MDB',tag='RYB',source_quotes=['R','Y','B']),
            dict(category='CT',name='Inferred CT',spec='',quantity=3,panel_code='MDB',tag='CT',source_quotes=['3xCT'])]}
        rows,warnings=merge_additions([main],payload,source)
        self.assertEqual([(d.tag,d.quantity) for d in rows],[('Q0',1),('FU',3),('RYB',3)])
        self.assertEqual(rows[0].icu_ka,None)
        self.assertEqual(rows[0].spec,'3P 150A 22kA')
        self.assertTrue(any('CT' in w for w in warnings))

    def test_review_cannot_duplicate_existing_tag_or_reuse_it_for_another_category(self):
        main=Device(category='MCB',name='Branch',spec='2P 16A',quantity=1,panel_code='P',tag='Q1')
        payload={'devices':[dict(category='FUSE',name='duplicate',spec='',quantity=1,
            panel_code='P',tag='Q1',source_quotes=['Q1'])]}
        rows,_=merge_additions([main],payload,[{'text':'Q1'}])
        self.assertEqual(rows,[main])


if __name__=='__main__':unittest.main()

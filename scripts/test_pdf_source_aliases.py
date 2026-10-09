import json
import unittest
from pathlib import Path
from app.schemas.ai import ExtractedDeviceSchema as Device
from app.services.ai.takeoff_integrity import normalize_takeoff


class SourceAliasTests(unittest.TestCase):
    def test_observed_pdf_duplicates_do_not_inflate_bom(self):
        rows = [Device(**r) for r in json.loads((Path(__file__).parent / 'fixtures/pdf_alias_takeoff.json').read_text(encoding='utf8'))]
        result, warnings = normalize_takeoff(rows)
        self.assertEqual(len(result), 27)
        self.assertEqual(sum(d.quantity for d in result), 27)
        self.assertEqual(len([d for d in result if d.category == 'LIGHT']), 3)
        self.assertEqual(len([d for d in result if d.category == 'MCCB']), 1)
        self.assertEqual(len([d for d in result if d.category == 'CB']), 20)
        self.assertTrue(warnings)
        self.assertEqual(len(normalize_takeoff(result)[0]), 27)

    def test_distinct_numbered_devices_and_pages_are_preserved(self):
        def row(tag, page=1):
            return Device(category='FUSE', name='Cầu chì', spec='6A', tag=tag, panel_code='P', source_filename='a.pdf', source_page=page)
        for rows in ([row('FU1'), row('FU2')], [row('Fuse',1), row('FU-METER',2)]):
            self.assertEqual(len(normalize_takeoff(rows)[0]), 2)

    def test_conflicting_ratings_are_not_merged(self):
        rows = [Device(category='CB',name='Lộ L1',spec='2P',tag=t,in_a=a,panel_code='P',source_filename='a.pdf') for t,a in [('L1/r',10),('L1',20)]]
        self.assertEqual(len(normalize_takeoff(rows)[0]), 2)


if __name__ == '__main__':
    unittest.main()

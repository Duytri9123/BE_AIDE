import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.import_schneider_extended_prices import extract


class Page:
    def __init__(self,text=''):self.text=text
    def get_text(self,*args,**kwargs):return self.text


class SchneiderImportTests(unittest.TestCase):
    def extract_fixture(self,text):
        pages=[Page() for _ in range(282)];pages[57]=Page(text)
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'book.pdf';source.write_bytes(b'reviewed source fixture')
            with patch('scripts.import_schneider_extended_prices.pymupdf.open',return_value=pages):
                return extract(source)

    def test_unknown_model_never_inherits_previous_frame(self):
        rows=self.extract_fixture('CVS400F 320 LV540305 17.151.200 LV540308 19.859.400\n'
            'CVS639F 500 LV563305 23.241.900 LV563308 29.057.600\n'
            '600 LV563306 26.821.300 LV563309 30.847.300')
        self.assertEqual(len(rows),2)
        self.assertEqual({r['specifications']['Họ thiết bị'] for r in rows},{'CVS400'})
        self.assertFalse(any(r['sku'].startswith('LV563') for r in rows))

    def test_bs_and_pole_columns_remain_separate(self):
        rows=self.extract_fixture('CVS100BS 16 LV510930 3.555.200 LV510950 4.803.700')
        self.assertEqual([r['specifications']['Số cực'] for r in rows],['3P','4P'])
        self.assertEqual([r['price'] for r in rows],[3555200,4803700])
        self.assertTrue(all(r['specifications']['Họ thiết bị']=='CVS100BS' for r in rows))
        self.assertTrue(all(r['specifications']['Điện áp Icu']=='380 V' for r in rows))


if __name__=='__main__':unittest.main()

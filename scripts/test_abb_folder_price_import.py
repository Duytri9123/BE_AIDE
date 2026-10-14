import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.import_abb_pricebook import extract_rows
from app.services.library_price_matching import configuration_links


class Page:
    def __init__(self,text='',words=()):self.text=text;self.words=words
    def get_text(self,mode=None,**kwargs):return self.words if mode=='words' else self.text


class Document:
    def __len__(self):return 218
    def __getitem__(self,index):
        return {28:Page('BẢNG GIÁ 2026'),34:Page(
            'XT1B 160 TMD 16-450 16 1SDA066799R1 3,611,000 1SDA066810R1 4,874,000\n'
            'XT1B 160 TMD 125-1250 125 InN=50% 1SDA068819R1 6,580,000',
            [(320,0,0,0,'1SDA066799R1'),(445,0,0,0,'1SDA066810R1'),(445,0,0,0,'1SDA068819R1')]),
            148:Page('FH202 AC-25/0.03 2CSF202006R1250 1,708,000'),
            149:Page('DS201 L C6 AC30 2CSR245080R1064 2,187,000'),
            115:Page('AX09 AX40 VE5-1 1SBN030110R1000 744,000\nAX09 AX40 VE5-1 1SBN030110R1000 744,000')}.get(index,Page())


class AbbFolderImportTests(unittest.TestCase):
    def rows(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'fixture.pdf';path.write_bytes(b'reviewed table fixture')
            with patch('scripts.import_abb_pricebook.pymupdf.open',return_value=Document()):return extract_rows(path)

    def test_columns_and_single_right_hand_code_preserve_poles_and_neutral(self):
        rows={r['sku']:r for r in self.rows()}
        self.assertEqual(rows['1SDA066799R1']['specifications']['Số cực'],'3P')
        right=rows['1SDA068819R1']
        self.assertEqual(right['specifications']['Số cực'],'4P')
        self.assertEqual(right['specifications']['Dòng cực N (%)'],'50')
        self.assertEqual(right['price'],6580000)

    def test_residual_current_and_accessory_rows_keep_real_fields(self):
        rows=self.rows()
        self.assertEqual(len(rows),6)
        fh=next(r for r in rows if r['category']=='RCCB')
        self.assertEqual(fh['specifications']['Dòng rò (mA)'],'30 mA')
        ds=next(r for r in rows if r['category']=='RCBO')
        self.assertEqual(ds['specifications']['Số cực'],'1P+N')
        self.assertEqual(ds['price'],2187000)
        self.assertEqual(sum(r['category']=='INTERLOCK' for r in rows),1)

    def test_xt_frame_is_manual_choice_and_never_matches_legacy_t(self):
        row=next(r for r in self.rows() if r['sku']=='1SDA066799R1')
        device={'id':'CAD','brand':'ABB','brand_identification_status':'verified','type':'MCCB','product_code':'XT1','spec':{'so_cuc':'3P'}}
        self.assertEqual(configuration_links(device,[row]),{row['id']:'CAD'})
        self.assertEqual(configuration_links({**device,'product_code':'T1'},[row]),{})
        self.assertEqual(configuration_links({**device,'spec':{'so_cuc':'4P'}},[row]),{})


if __name__=='__main__':unittest.main()

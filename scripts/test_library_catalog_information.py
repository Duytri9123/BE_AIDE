import unittest
from app.services.library_catalog_information import information_rows,optional_price


class CatalogInformationTests(unittest.TestCase):
    def row(self,code,price=None):
        return {'id':code,'sku':code,'brand':'ABB','category':'MCCB','price':price,
            'item_name':'MCCB '+code,'columns':['Tên hàng','Dòng điện','Giá'],
            'cells':['MCCB '+code,'16 A','the original price cell'],
            'specifications':{'Dòng điện':'16 A'},'source_url':'https://example.com/catalog.pdf'}

    def device(self):
        return {'brand':'ABB','product_code':'A1','type':'MCCB','catalog_references':
            {'category':'MCCB','options':[{'brand':'ABB','model':'A1'},{'brand':'ABB','model':'A2'}]}}

    def test_original_unpriced_rows_and_cells_are_preserved(self):
        rows=information_rows(self.device(),[self.row('A1-16'),self.row('A2-16',1200)])
        self.assertEqual({r['sku'] for r in rows},{'A1-16','A2-16'})
        unpriced=next(r for r in rows if r['sku']=='A1-16')
        self.assertIsNone(unpriced['price'])
        self.assertEqual(unpriced['cells'],self.row('A1-16')['cells'])
        self.assertEqual(unpriced['specifications'],{'Dòng điện':'16 A'})
        self.assertTrue(all(r['identity_verified'] is False for r in rows))

    def test_zero_invalid_prices_do_not_remove_information(self):
        for price in (0,-1,float('nan'),float('inf'),True,'1000',None):
            with self.subTest(price=price):
                self.assertIsNone(optional_price(price))
                self.assertEqual(len(information_rows(self.device(),[self.row('A1-16',price)])),1)

    def test_numeric_boundaries_and_row_identity(self):
        device=self.device();device['catalog_references']['options']=[{'brand':'ABB','model':'A1'}]
        rows=information_rows(device,[self.row('A1-16'),self.row('A100-16')])
        self.assertEqual([r['sku'] for r in rows],['A1-16'])
        device['catalog_references']['options'].append({'source_row_id':'A100-16'})
        self.assertEqual(len(information_rows(device,[self.row('A1-16'),self.row('A100-16')])),2)

    def test_marketing_family_and_order_code_are_distinct(self):
        device=self.device();device['spec']={'so_cuc':'1P'}
        row=self.row('1SDA066485R1');row.update(item_name='A1C TMF 1P 15A',group='MCCB · A1')
        row['specifications']['Số cực']='1P'
        other=self.row('1SDA-OTHER');other.update(item_name='A1C TMF 3P 15A',group='MCCB · A1')
        other['specifications']['Số cực']='3P'
        result=information_rows(device,[row,other])
        self.assertEqual([r['sku'] for r in result],['1SDA066485R1'])
        self.assertEqual(result[0]['match_scope'],'source_family')

    def test_catalog_only_model_without_price_is_visible(self):
        device=self.device();device['catalog_references']['options']=[{'brand':'ABB','model':'A1',
            'specifications':{'Tên hàng':'A1 example','Số cực':'1P'},'price':'---'}]
        result=information_rows(device,[])
        self.assertEqual(result[0]['sku'],'A1')
        self.assertIsNone(result[0]['price'])
        self.assertEqual(result[0]['cells'],['A1 example','A1','Số cực: 1P'])

    def test_reviewed_exact_row_overrides_broad_option_candidate(self):
        from unittest.mock import patch
        device=self.device()
        row=self.row('other-sku',1200)
        device['catalog_references'].update(source_row_scope='explicit_only',row_links_reviewed=True,
            options=[{'brand':'ABB','model':'A2','source_row_id':row['id']}])
        # The broad option resolver sees the row before the reviewed ID branch.
        with patch('app.services.library_catalog_information.reference_matches',return_value=[row]):
            result=information_rows(device,[row])
        self.assertEqual(result[0]['match_scope'],'source_family')
        self.assertEqual(result[0]['cells'],row['cells'])

    def test_reviewed_row_does_not_bypass_pole_filter(self):
        device=self.device();device['spec']={'so_cuc':'1P'}
        row=self.row('A2',1200);row['specifications']['Số cực']='3P'
        device['catalog_references'].update(source_row_scope='explicit_only',row_links_reviewed=True,
            options=[{'brand':'ABB','source_row_id':row['id']}])
        self.assertEqual(information_rows(device,[row]),[])

    def test_ls_same_series_different_frame_stays_candidate(self):
        device={'brand':'LS Electric','product_code':'ABN 100','display':'LS MCCB ABN 100',
                'type':'MCCB','spec':{'so_cuc':'2P'},'catalog_references':{'category':'MCCB','options':[]}}
        row={'id':'wrong-frame','sku':'ABN202c','brand':'LS Electric','category':'MCCB',
             'specifications':{'Số cực':'2P'},'price':10}
        result=information_rows(device,[row])
        self.assertEqual(result[0]['match_scope'],'catalog_reference')
        self.assertEqual(result[0]['basis'],'catalog_series_reference')

    def test_acb_complete_model_alternative_matches_configuration_suffix(self):
        device={'brand':'LS Electric','product_code':'AN-06D3 / AN-08D3',
                'type':'ACB','spec':{'so_cuc':'3P'},'catalog_references':{'category':'ACB','options':[]}}
        rows=[{'id':s,'sku':s,'brand':'LS Electric','category':'ACB',
               'specifications':{'Số cực':'3P'},'price':10} for s in ['AN-06D3-06H AH6','AN-10D3-10H AH6']]
        result=information_rows(device,rows)
        self.assertEqual(next(r for r in result if r['sku']==rows[0]['sku'])['match_scope'],'source_family')
        self.assertTrue(all(r['match_scope']=='catalog_reference' for r in result if r['sku']==rows[1]['sku']))

    def test_manufacturer_table_excludes_other_makers_even_with_explicit_references(self):
        device=self.device()
        device['catalog_references']['options'].append({'brand':'CHINT','model':'NM8',
            'source_row_id':'NM8','specifications':{'Số cực':'1P'}})
        abb=self.row('A1-16');abb['source_kind']='supplier_pricebook'
        other={**self.row('NM8'),'brand':'CHINT'}
        rows=information_rows(device,[abb,other])
        self.assertEqual([r['brand'] for r in rows],['ABB'])
        self.assertEqual(rows[0]['columns'],abb['columns'])
        self.assertEqual(rows[0]['cells'],abb['cells'])
        self.assertEqual(rows[0]['information_kind'],'pricebook')


if __name__=='__main__':unittest.main()

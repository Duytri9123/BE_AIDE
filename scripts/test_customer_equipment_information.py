import json
import unittest
from app.services.customer_equipment_information import customer_device,customer_information_rows,external_url,public_view_id,product_specs


class CustomerEquipmentTests(unittest.TestCase):
    def test_no_private_evidence_and_no_other_brand_suggestions(self):
        raw={'id':'TB-x','display':'MCCB ABB A1','brand':'ABB','spec':{'so_cuc':'1P','nhan_block_nguon':'secret'},
            'source_identification':{'profile':'private/file.json'},'source_catalog_review':{'handle':'ABC'},
            'primary_view':'SOURCE-SECRET','views':[{'id':'SOURCE-SECRET','label':'Mặt trước','face':'Mặt trước',
                'preview':'/equipment-library/TB-x/views/SOURCE-SECRET/preview','source_info':{'Nguồn':'private'}}],
            'catalog_references':{'research':{'status':'private'},'options':[
                {'brand':'ABB','model':'A1','specifications':{'Số cực':'1P','Căn cứ':'Nhãn CAD nguồn','Trang tài liệu':4},'source_url':'https://new.abb.com/products'},
                {'brand':'Hager','model':'X','specifications':{'Số cực':'1P'}}]}}
        item=customer_device(raw)
        self.assertEqual([o['brand'] for o in item['catalog_references']['options']],['ABB'])
        text=json.dumps(item)
        for secret in ('SOURCE-SECRET','private/file','source_catalog_review','source_identification','Căn cứ','Trang tài liệu','nhan_block'):self.assertNotIn(secret,text)
        self.assertEqual(item['primary_view'],public_view_id('SOURCE-SECRET'))
        self.assertEqual(item['spec'],{'so_cuc':'1P'})
        self.assertEqual([o['brand'] for o in item['other_brand_references']],['Hager'])

    def test_reference_rows_are_deduplicated_without_drawing_measurements(self):
        raw={'id':'test-only','brand':'ABB','display':'ABB A3','views':[],
             'catalog_references':{'options':[
                 {'brand':'ABB','model':'A3','specifications':{'Căn cứ':'CAD nguồn'}},
                 {'brand':'ABB','model':'A3','specifications':{'Số cực':'3P','Hình chiếu Mặt bên':'100x200','Lắp đặt tham khảo':'generic'}},
                 {'brand':'ABB','model':'A3','specifications':{'Số cực':'3P'}},
                 {'brand':'CHINT','model':'NM8','specifications':{'Số cực':'3P'}}]}}
        result=customer_device(raw)
        self.assertEqual(len(result['catalog_references']['options']),1)
        self.assertEqual(result['catalog_references']['options'][0]['specifications'],{'Số cực':'3P'})
        self.assertEqual(result['other_brand_references'][0]['brand'],'CHINT')

    def test_product_rows_keep_specifications_and_external_documents(self):
        row={'id':'x','sku':'A1','item_name':'A1 1P','brand':'ABB','price':None,
             'source_page':99,'source_url':'https://new.abb.com/catalog.pdf','basis':'private','columns':['Tên hàng','Số cực'],'cells':['A1','1P']}
        result=customer_information_rows([row],{'brand':'ABB'})
        self.assertEqual(len(result),1)
        self.assertNotIn('source_page',result[0]);self.assertNotIn('basis',result[0])
        self.assertEqual(result[0]['source_url'],row['source_url'])
        self.assertIsNone(result[0]['price'])
        self.assertFalse(external_url('/device-catalog/documents/private'))
        self.assertFalse(external_url('https://127.0.0.1/private'))

    def test_offers_without_table_columns_keep_name_specs_and_optional_price(self):
        row={'id':'offer','brand':'Hager','sku':'HDA018Z','name':'MCCB 1P 20A 18kA',
             'price':1056990,'information_kind':'price_reference',
             'specifications':{'Số cực':'1P','In (A)':'20','nguon':'private'},
             'source_url':'https://www.hager.com/product/HDA018Z','source_page':4}
        item=customer_information_rows([row],{'brand':'Hager'})[0]
        self.assertEqual(item['columns'],['Tên hàng','Mã hàng','Số cực','In (A)','Giá bán'])
        self.assertEqual(item['cells'][:2],[row['name'],'HDA018Z'])
        self.assertEqual(item['cells'][2:4],['1P','20'])
        self.assertNotIn('private',json.dumps(item))
        self.assertEqual(item['price'],1056990)
        self.assertNotIn('columns',row)

    def test_original_schema_survives_empty_cells_and_embedded_private_evidence(self):
        row={'id':'a','brand':'ABB','sku':'A1','columns':['Tên hàng','Mã đặt hàng','Ghi chú','Thông số','Giá bán'],
             'cells':['A1','1SDA','', '16 A; Căn cứ: nhãn CAD nguồn; Phạm vi: mã trên bản vẽ', '1,000'],
             'price':1000,'information_kind':'pricebook'}
        result=customer_information_rows([row],{'brand':'ABB'})[0]
        self.assertEqual(result['columns'],row['columns'])
        self.assertEqual(result['cells'],['A1','1SDA','','16 A','1,000'])
        self.assertEqual(result['information_kind'],'pricebook')

    def test_catalog_json_fallback_is_replaced_by_product_facts(self):
        row={'id':'offer','brand':'LS Electric','sku':'BKN 2P 25A','name':'MCB LS BKN 25A 2P',
             'information_kind':'price_reference','price':None,
             'columns':['Tên hàng','Mã hàng','Thông tin'],'cells':['BKN','BKN','{}'],
             'specifications':{'Số cực':'2P','Dòng chỉnh định':'Chưa xác định'}}
        item=customer_information_rows([row],{'brand':'LS Electric'})[0]
        self.assertEqual(item['cells'][2],'2P')
        self.assertNotIn('{}',item['cells'])
        self.assertNotIn('Chưa xác định',item['cells'][2])

    def test_pricebook_page_boundaries_share_book_identity(self):
        common={'brand':'ABB','information_kind':'pricebook','source_url':'https://abb.com/prices.pdf',
                'group':'MCCB','columns':['Mã hàng','Giá bán'],'cells':['A1','100'],'price':100}
        rows=[{**common,'id':'a','sku':'A1','book_key':'page1','source_page':1},
              {**common,'id':'b','sku':'A2','book_key':'page2','source_page':2}]
        result=customer_information_rows(rows,{'brand':'ABB'})
        self.assertEqual(result[0]['book_key'],result[1]['book_key'])

    def test_drawing_metadata_is_hidden_but_supply_specification_is_preserved(self):
        spec={'nhan_tren_cad':'private','so_hinh_cung_nhan':4,'ma_ung_vien':'X',
              'Nguồn cấp':'230 VAC','loai_nguon':'AC','so_cuc':'4P',
              'kha_nang_cat':'Chọn Icu/Ics theo mã'}
        self.assertEqual(product_specs(spec),{'Nguồn cấp':'230 VAC','loai_nguon':'AC','so_cuc':'4P'})


if __name__=='__main__':unittest.main()

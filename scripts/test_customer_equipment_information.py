import json
import unittest
from app.services.customer_equipment_information import customer_device,customer_information_rows,external_url,public_view_id


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

    def test_original_schema_survives_empty_cells_and_embedded_private_evidence(self):
        row={'id':'a','brand':'ABB','sku':'A1','columns':['Tên hàng','Mã đặt hàng','Ghi chú','Thông số','Giá bán'],
             'cells':['A1','1SDA','', '16 A; Căn cứ: nhãn CAD nguồn; Phạm vi: mã trên bản vẽ', '1,000'],
             'price':1000,'information_kind':'pricebook'}
        result=customer_information_rows([row],{'brand':'ABB'})[0]
        self.assertEqual(result['columns'],row['columns'])
        self.assertEqual(result['cells'],['A1','1SDA','','16 A','1,000'])
        self.assertEqual(result['information_kind'],'pricebook')


if __name__=='__main__':unittest.main()

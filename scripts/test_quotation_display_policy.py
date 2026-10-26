import copy
import tempfile
import unittest
from unittest.mock import patch
from openpyxl import load_workbook
from app.services.export.quotation_names import quotation_name
from app.services.export.quotation_exporter import QuotationExporterService
from app.services.ai.procurement_review import supplement_enclosure_details

class QuotationDisplayPolicy(unittest.TestCase):
    def test_auxiliary_default_only_changes_display_name(self):
        source={'category':'LIGHT','name':'Đèn báo pha R','brand':None,'spec':'220V'}
        before=copy.deepcopy(source)
        self.assertEqual(quotation_name(source),'Đèn báo pha R Asian')
        self.assertEqual(source,before)
        self.assertEqual(quotation_name({'category':'MCB','name':'MCB 3P'}),'MCB 3P')
        self.assertEqual(quotation_name({'category':'SHUNT_TRIP','name':'Cuộn cắt'}),'Cuộn cắt')

    def test_explicit_identities_and_existing_default_are_preserved(self):
        for item in ({'brand':'Schneider'},{'part_number':'XB4BVB3'},{'origin':'CHINT'}):
            self.assertEqual(quotation_name({'category':'LIGHT','name':'Đèn báo',**item}),'Đèn báo')
        self.assertEqual(quotation_name({'category':'LIGHT','name':'Đèn báo Asian'}),'Đèn báo Asian')
        self.assertEqual(quotation_name({'category':'LIGHT','name':'Đèn báo','origin':'VN'}),'Đèn báo Asian')

    def test_excel_name_does_not_fabricate_origin_or_price(self):
        with tempfile.TemporaryDirectory() as directory:
            rows=[{'row_type':'panel_header','name':'P'}, {'row_type':'item','category':'LIGHT','name':'Đèn báo','origin':'','quantity':3,'unit_price':None}]
            with patch('app.services.export.quotation_exporter.settings.EXPORT_DIR',directory):
                path=QuotationExporterService.export(rows,proposals=[])
                wb=load_workbook(path)
                row=list(wb.active.values)[2]
                self.assertEqual(row[1],'Đèn báo Asian')
                self.assertIsNone(row[3])
                self.assertEqual(row[6],'Chờ báo giá')
                wb.close()
            self.assertEqual(rows[1]['name'],'Đèn báo')

    def test_design_supplements_existing_enclosure_without_duplicates(self):
        rows=[{'row_type':'panel_header','name':'P'}, {'id':'P-assembly-ENCLOSURE','row_type':'accessory','name':'Vỏ tủ','spec':'','unit_price':None}]
        reviewed=supplement_enclosure_details(rows,{'height':2300,'width':1000,'depth':250,'thickness':'2 mm','door_count':2})
        self.assertEqual(len(reviewed),len(rows))
        self.assertIn('H2300 x W1000 x D250',reviewed[1]['spec'])
        self.assertIn('Số cửa: 2',reviewed[1]['spec'])
        self.assertIsNone(reviewed[1]['unit_price'])
        self.assertEqual(rows[1]['spec'],'')
        self.assertEqual(supplement_enclosure_details(rows,{'status':'needs_dimensions'}),rows)

if __name__=='__main__': unittest.main()

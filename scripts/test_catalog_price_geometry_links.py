"""Regression checks for numeric ordering codes and incompatible CAD bodies."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.catalog_price_geometry_links import family_link
from app.services.library_reference_prices import reference_matches

class Links(unittest.TestCase):
 def setUp(self):
  self.raw={'ma_dong_san_pham':'A1'}
  self.device={'spec':{'so_cuc':'3P'},'brand':'ABB','type':'MCCB','poles':'3P','product_code':'A1','name':'MCCB ABB A1 3P'}
  self.row={'brand':'ABB','sku':'1SDA012345','item_name':'A1B 125','category':'MCCB','specifications':{'Họ thiết bị':'A1','Số cực':'3P','In (A)':'100'}}
 def test_numeric_order_code(self):self.assertIsNotNone(family_link(self.raw,self.device,self.row))
 def test_other_brand(self):
  self.row['brand']='LS';self.assertIsNone(family_link(self.raw,self.device,self.row))
 def test_other_poles(self):
  self.row['specifications']['Số cực']='4P';self.assertIsNone(family_link(self.raw,self.device,self.row))
 def test_over_frame(self):
  self.row['specifications']['In (A)']='250';self.assertIsNone(family_link(self.raw,self.device,self.row))
 def test_other_family(self):
  self.row['specifications']['Họ thiết bị']='A2';self.assertIsNone(family_link(self.raw,self.device,self.row))
 def test_numeric_sku_with_explicit_row(self):
  row={'id':'mitsubishi-1','sku':'100123','brand':'Mitsubishi Electric','category':'MCB'}
  self.assertEqual(reference_matches({'brand':row['brand'],'model':row['sku'],'source_row_id':row['id']},'MCB',[row]),[row])
 def test_numeric_sku_without_evidence(self):
  row={'id':'mitsubishi-1','sku':'100123','brand':'Mitsubishi Electric','category':'MCB'}
  self.assertEqual(reference_matches({'brand':row['brand'],'model':row['sku']},'MCB',[row]),[])
if __name__=='__main__':unittest.main()

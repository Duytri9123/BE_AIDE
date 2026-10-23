"""Native terminal variants must not inherit same-name, different-body prices."""
import unittest
from app.services.library_catalog_information import information_rows

class ExplicitRowScopeTests(unittest.TestCase):
 def rows(self):
  return [dict(id=i,sku='BM630s-LTA',item_name='BM630s-LTA 3P',brand='Shihlin',category='MCCB',price=p,specifications={'Số cực':'3P'}) for i,p in [('bare',10756000),('equipped',11629000)]]
 def device(self,options):
  return dict(brand='Shihlin',product_code='BM630s-LTA',type='MCCB',spec={'so_cuc':'3P'},catalog_references={'category':'MCCB','source_row_scope':'explicit_only','options':options})
 def test_same_model_pole_other_terminal_price_excluded(self):
  d=self.device([dict(brand='Shihlin',model='BM630s-LTA',source_row_id='equipped')])
  rows=information_rows(d,self.rows())
  self.assertEqual([r['price'] for r in rows],[11629000])
 def test_missing_or_stale_reference_never_falls_back_to_family_prices(self):
  for options in [[],[dict(brand='Shihlin',model='BM630s-LTA',source_row_id='missing')]]:
   self.assertEqual(information_rows(self.device(options),self.rows()),[])
 def test_unrestricted_existing_family_behavior_preserved(self):
  d=self.device([]);d['catalog_references'].pop('source_row_scope')
  self.assertEqual(len(information_rows(d,self.rows())),2)

if __name__=='__main__':unittest.main()

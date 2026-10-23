import unittest,tempfile,hashlib
from pathlib import Path
from app.services.catalog_projection_review import apply_projection_review

class ProjectionReviewTests(unittest.TestCase):
 def fixture(self,root):
  path=Path(root)/'profile.json';drawing=Path(root)/'view.dxf';drawing.write_bytes(b'original drawing')
  review={'status':'orientation_identified','source_dxf_sha256':hashlib.sha256(drawing.read_bytes()).hexdigest(),'reviewed_label':'Mặt trước · bảng nhiều thiết bị'}
  raw={'ten_san_pham':'Bảng thiết bị CHINT NP2','nhan_dien_ai':{'loai_thiet_bi_code':'ASSEMBLY_REFERENCE'},'source_catalog_review':{'contains_multiple_components':True},'cad_don':[{'id_hinh_goc':'v1','duong_dan':'view.dxf','huong_nhin':review['reviewed_label'],'orientation_review':review}]}
  profile={'type':'PUSHBUTTON','product_code':'NP2','views':[{'id':'v1','label':'Chưa xác nhận hướng nhìn','face':'unknown'}]}
  return path,drawing,raw,profile
 def test_whole_sheet_cannot_revert_to_single_button(self):
  with tempfile.TemporaryDirectory() as root:
   p,f,r,d=self.fixture(root);self.assertTrue(apply_projection_review(d,r,p));self.assertEqual(d['type'],'ASSEMBLY_REFERENCE');self.assertIsNone(d['product_code']);self.assertFalse(d['auto_select']);self.assertEqual(d['catalog_references']['options'],[])
 def test_changed_source_does_not_receive_old_review(self):
  with tempfile.TemporaryDirectory() as root:
   p,f,r,d=self.fixture(root);f.write_bytes(b'different drawing');self.assertFalse(apply_projection_review(d,r,p));self.assertEqual(d['type'],'PUSHBUTTON');self.assertEqual(d['views'][0]['face'],'unknown')
 def test_changed_label_needs_another_review(self):
  with tempfile.TemporaryDirectory() as root:
   p,f,r,d=self.fixture(root);r['cad_don'][0]['huong_nhin']='Mặt bên';self.assertFalse(apply_projection_review(d,r,p))
if __name__=='__main__':unittest.main()

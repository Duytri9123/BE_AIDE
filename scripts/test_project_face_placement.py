import os,sys,io,tempfile,unittest,logging
logging.disable(logging.CRITICAL)
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'BE_AIDE'))
if sys.version_info[:2]==(3,12):sys.path.insert(0,str(ROOT/'tmp/tudien_deps'))
os.environ.setdefault('DATABASE_URL','sqlite+aiosqlite:///:memory:')
os.environ.setdefault('SECRET_KEY','local-regression-test-only')
import ezdxf
from app.services.cad.source_project_generator import SourceProjectGenerator as G
from app.services.cad.catalogtb_assets import candidates
from app.services.cad.physical_layout_engine import PhysicalLayoutEngine as P,MountingType
from app.schemas.ai import ExtractedDeviceSchema

class FacePlacement(unittest.TestCase):
 def test_schema_preserves_face_and_independent_sources(self):
  d=ExtractedDeviceSchema(category='SELECTOR',name='CM',spec='3 vị trí',mounting_face='inner_door',source_observations={'schematic':{'quantity':1}}).model_dump()
  self.assertEqual(d['mounting_face'],'inner_door');self.assertEqual(d['source_observations']['schematic']['quantity'],1)
 def test_face_assignment_survives_actual_geometry_insertion(self):
  doc=ezdxf.new('R2018');doc.units=4
  faces=[{'kind':f,'clean_bounds':[x,0,x+500,700]} for f,x in [('mounting_plate',0),('inner_door',1000),('outer_door',2000)]]
  item={'faces':faces};dim={'width':500,'height':700,'depth':250}
  cb=candidates('MCB','LS',1)[0];sel=candidates('SELECTOR')[0];meter=candidates('METER',measurement_function='current')[0]
  devices=[{'tag':'M1','category':'MCB','cad':{'asset_id':cb['id']}},
           {'tag':'M2','category':'MCB','cad':{'asset_id':cb['id']}},
           {'tag':'CM','category':'SELECTOR','mounting_face':'inner_door','cad':{'asset_id':sel['id']}},
           {'tag':'A','category':'METER','mounting_face':'outer_door','cad':{'asset_id':meter['id']}}]
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'form.dxf';doc.saveas(path);s=io.StringIO();doc.write(s)
   with patch('app.services.cad.cabinet_templates.source_path',return_value=path):
    _,places,missing=G._place_devices(s.getvalue(),devices,dim,item)
   bytag={p['tag']:p for p in places};self.assertFalse(missing)
   self.assertEqual(bytag['CM']['mounting_face'],'inner_door');self.assertGreater(bytag['CM']['x'],1000)
   self.assertEqual(bytag['A']['mounting_face'],'outer_door');self.assertGreater(bytag['A']['x'],2000)
   self.assertAlmostEqual(bytag['M2']['x'],bytag['M1']['x']+bytag['M1']['width'])
   devices[2].pop('mounting_face')
   with patch('app.services.cad.cabinet_templates.source_path',return_value=path),self.assertRaisesRegex(ValueError,'vùng cánh'):
    G._place_devices(s.getvalue(),devices,dim,item)
 def test_project_inner_door_overrides_default(self):
  self.assertEqual(P.classify_mounting({'category':'SELECTOR','mounting_face':'inner_door'}),MountingType.INNER_COVER_MOUNTED)
  self.assertEqual(P.classify_mounting({'category':'SELECTOR'}),MountingType.DOOR_MOUNTED)
  self.assertEqual(P.classify_mounting({'category':'CONTACTOR'}),MountingType.DIN_RAIL_MOUNTED)

if __name__=='__main__':unittest.main(verbosity=2)

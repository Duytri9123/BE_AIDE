"""Extract explicit supplier projection blocks at native millimetre scale."""
import hashlib
import json
import urllib.request
from pathlib import Path
import ezdxf
from ezdxf import bbox
from ezdxf.addons import Importer
from ezdxf.addons.drawing import matplotlib
from ezdxf.disassemble import recursive_decompose
from ezdxf.math import Matrix44

ROOT=Path(__file__).resolve().parents[1]/'data/CatalogTB'
SOURCES={
 'XT1':('1SDH000719R0100',{'3P':'BLOCK53','4P':'BLOCK34','side':'BLOCK72'}),
 'XT2':('1SDH000721R0100',{'3P':'BLOCK35','4P':'BLOCK69','side':'BLOCK93'}),
 'XT3':('1SDH000720R0100',{'3P':'BLOCK42','4P':'BLOCK98','side':'BLOCK59'}),
 'XT4':('1SDH000722R0100',{'3P':'BLOCK68','4P':'BLOCK40','side':'BLOCK84'}),
}


def main():
 report=[]
 for family,(uid,blocks) in SOURCES.items():
  folder=ROOT/'ABB/NguonBenNgoai'/uid
  folder.mkdir(parents=True,exist_ok=True)
  source=folder/f'ABB_MCCB_Tmax_{family}_3P-4P_Fixed_F_source.dxf'
  if not source.exists():
   url=f'https://search.abb.com/library/Download.aspx?DocumentID={uid}&LanguageCode=en&LanguageCode=it&DocumentPartId=&Action=Launch'
   with urllib.request.urlopen(url,timeout=60) as response:content=response.read()
   if b'SECTION' not in content[:100]:raise ValueError('Supplier response is not a DXF')
   source.write_bytes(content)
   (folder/'source.json').write_text(json.dumps({'url':url,'document_id':uid,'sha256':hashlib.sha256(content).hexdigest(),'bytes':len(content),'checked_at':'2026-10-20'},indent=2),encoding='utf8')
  doc=ezdxf.readfile(source)
  metadata=json.loads((folder/'source.json').read_text(encoding='utf8'))
  for variant,block in blocks.items():
   anchor=next(e for e in doc.modelspace().query('INSERT') if e.dxf.name==block)
   base=list(recursive_decompose([anchor])); bounds=bbox.extents(base)
   selected=[]
   for insert in doc.modelspace().query('INSERT'):
    if insert.dxf.insert!=anchor.dxf.insert or insert.dxf.xscale!=anchor.dxf.xscale:continue
    entities=list(recursive_decompose([insert])); box=bbox.extents(entities)
    if any(e.dxftype() in {'TEXT','MTEXT','DIMENSION','LEADER'} for e in entities):continue
    if box.has_data and all(box.extmin[i]>=bounds.extmin[i]-.001 and box.extmax[i]<=bounds.extmax[i]+.001 for i in (0,1)):
     selected.extend(entities)
   target=ezdxf.new('R2010');target.units=4
   importer=Importer(doc,target); importer.import_entities(selected);importer.finalize()
   matrix=Matrix44.chain(Matrix44.translate(-bounds.extmin.x,-bounds.extmin.y,0),Matrix44.scale(1/anchor.dxf.xscale))
   for entity in target.modelspace():entity.transform(matrix)
   name=f'ABB_MCCB_Tmax_{family}_{variant}_Fixed_F'
   out=folder/name;out.mkdir(exist_ok=True)
   drawing=out/'ban_ve.dxf';target.saveas(drawing)
   matplotlib.qsave(target.modelspace(),str(out/'preview.png'),dpi=110)
   size=bbox.extents(target.modelspace()).size
   evidence={'source_url':metadata['url'],'document_id':uid,'source_sha256':metadata['sha256'],
      'source_block':block,'sheet_insert_scale':anchor.dxf.xscale,'coordinate_scale_to_mm':1/anchor.dxf.xscale,
      'units':'mm','width_mm':size.x,'height_mm':size.y,'entity_count':len(target.modelspace()),
      'sha256':hashlib.sha256(drawing.read_bytes()).hexdigest(),'status':'supplier_projection_reference',
      'exact_electrical_variant_verified':False}
   (out/'evidence.json').write_text(json.dumps(evidence,indent=2),encoding='utf8')
   report.append({'family':family,'variant':variant,'directory':out.relative_to(ROOT).as_posix(),**evidence})
 (ROOT.parents[1]/'docs/abb-official-faces-2026-10-20.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 print(f'Extracted {len(report)} manufacturer projections')


if __name__=='__main__':main()

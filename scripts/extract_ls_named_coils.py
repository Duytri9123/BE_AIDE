"""Extract explicitly named supplier coil parts; never reuse the parent body as an accessory."""
from pathlib import Path
import json,hashlib
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.collections import Sequence_TDF_Label
from OCP.TDF import TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.STEPControl import STEPControl_Writer,STEPControl_AsIs
from OCP.IFSelect import IFSelect_RetDone
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'data/CatalogTB/LS/NguonBenNgoai'
JOBS=[('RU-746303b762979714/model-000','COIL_12_ASM','RU-COIL-MC18-AC','AC','Coil for MC6a, 9a, 12a, 18a, 9b, 12b, 18b, 22b'),('RU-746303b762979714/model-005','COIL_25AF_DC_ASM','RU-COIL-MC40-DC','DC','Coil for MC32a, 40a'),('RU-dbaf97f47308bfd7/model-005','COIL_50_ASM','RU-COIL-MC65-AC','AC','Coil for MC-50a, 65a'),('RU-dbaf97f47308bfd7/model-000','COIL_95_ASM','RU-COIL-MC100-AC','AC','Coil for MC-75a, 85a, 100a'),('RU-dbaf97f47308bfd7/model-002','COIL_T_ASSY_MC150_ASM','RU-COIL-MC150','AC/DC','Coil for MC-130a, 150a'),('RU-dbaf97f47308bfd7/model-003','MS2203601_ASM','RU-COIL-MC225-ASSEMBLY','AC/DC','Coil for MC-185a, 225a'),('RU-dbaf97f47308bfd7/model-004','4003601_ASM','RU-COIL-MC400-ASSEMBLY','AC/DC','Coil for MC-330a, 400a')]

def extract(job):
 source,name,ident,coil,sku=job;p=BASE/source/'source.stp';p=p if p.exists() else p.with_suffix('.step');out=BASE/ident
 if (out/'source.step').exists() and (out/'source.json').exists():return
 doc=TDocStd_Document(TCollection_ExtendedString('BinXCAF'));reader=STEPCAFControl_Reader();reader.SetNameMode(True);assert reader.ReadFile(str(p))==IFSelect_RetDone;assert reader.Transfer(doc);tool=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main());free=Sequence_TDF_Label();tool.GetFreeShapes(free);found=[]
 def walk(label,path=''):
  attr=TDataStd_Name();text=attr.Get().ToExtString() if label.FindAttribute(TDataStd_Name.GetID_s(),attr) else '?';here=path+'/'+text
  if text==name:found.append((label,here));return
  children=Sequence_TDF_Label()
  if tool.GetComponents_s(label,children):
   for i in range(1,children.Length()+1):
    c=children.Value(i);ref=TDF_Label();walk(ref if tool.GetReferredShape_s(c,ref) else c,here)
 for i in range(1,free.Length()+1):walk(free.Value(i))
 unique=[]
 for candidate in found:
  if not any(candidate[0].IsEqual(other[0]) for other in unique):unique.append(candidate)
 assert len(unique)==1,(ident,name,[x[1] for x in found]);label,path=unique[0];shape=tool.GetShape_s(label);assert not shape.IsNull();writer=STEPControl_Writer();assert writer.Transfer(shape,STEPControl_AsIs)==IFSelect_RetDone;out.mkdir(exist_ok=True);assert writer.Write(str(out/'source.step'))==IFSelect_RetDone
 meta=json.loads(p.with_name('source.json').read_text(encoding='utf8'));meta.update(source_url=meta.get('source_url') or meta['url'],parent_step_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),step_sha256=hashlib.sha256((out/'source.step').read_bytes()).hexdigest(),source_assembly_path=path,part_name=name,extraction_method='Named XCAF source part/subassembly only, with no parent contactor geometry',price_row_sku=sku,coil_kind=coil)
 (out/'source.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8');print(ident,path,flush=True)
if __name__=='__main__':
 import sys
 for job in JOBS:
  if len(sys.argv)>1 and job[2] not in sys.argv[1:]:continue
  extract(job)

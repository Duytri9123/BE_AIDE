"""Inspect actual STEP component identities before considering contact variants."""
import json
from pathlib import Path
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.collections import Sequence_TDF_Label
from OCP.TDF import TDF_Label
from OCP.IFSelect import IFSelect_RetDone
from step_named_assembly import label_name,bounds
from ls_native_writer import CAT,ROOT

def inspect(ident):
    source=CAT/'LS/NguonBenNgoai'/ident/'source.step'
    doc=TDocStd_Document(TCollection_ExtendedString('cad'))
    reader=STEPCAFControl_Reader();reader.SetNameMode(True)
    assert reader.ReadFile(str(source))==IFSelect_RetDone and reader.Transfer(doc)
    tool=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main());roots=Sequence_TDF_Label();tool.GetFreeShapes(roots)
    rows=[]
    def walk(label,path,depth):
        name=label_name(label);here=path+'/'+name
        if tool.IsReference_s(label):
            ref=TDF_Label();assert tool.GetReferredShape_s(label,ref);walk(ref,here,depth)
        else:
            if depth<3:
                shape=tool.GetShape_s(label)
                try:extent=bounds(shape)
                except Exception:extent=None
                rows.append(dict(name=name,path=here,depth=depth,bounds=extent))
            if tool.IsAssembly_s(label) and depth<3:
                children=Sequence_TDF_Label();tool.GetComponents_s(label,children,False)
                for i in range(1,children.Length()+1):walk(children.Value(i),here,depth+1)
    for i in range(1,roots.Length()+1):walk(roots.Value(i),'',0)
    print(ident,[(r['name'],r['depth']) for r in rows],flush=True)
    return dict(source=ident,components=rows)

if __name__=='__main__':
    out=ROOT/'docs/ls-all-cad-2026-10-24/dc-aux-review-20261026.json'
    out.write_text(json.dumps([inspect(i) for i in ['AMERICA-23721','AMERICA-26774','45351/model-000']],indent=2),encoding='utf8')

"""Remove only a named optional STEP assembly, preserving all original placements."""
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.STEPControl import STEPControl_Writer,STEPControl_AsIs
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_Label
from OCP.collections import Sequence_TDF_Label
from OCP.TDataStd import TDataStd_Name
from OCP.Interface import Interface_Static
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS_Compound
from OCP.BRep import BRep_Builder
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_RetDone

def bounds(shape):
 b=Bnd_Box();BRepBndLib.Add_s(shape,b,False);lo,hi=b.CornerMin(),b.CornerMax();return [lo.X(),lo.Y(),lo.Z(),hi.X(),hi.Y(),hi.Z()]
def volume(shape):
 p=GProp_GProps();BRepGProp.VolumeProperties_s(shape,p);return p.Mass()
def label_name(label):
 a=TDataStd_Name();return a.Get().ToExtString() if label.FindAttribute(TDataStd_Name.GetID_s(),a) else ''
def excluded_assembly(source,target,names):
 Interface_Static.SetCVal_s('xstep.cascade.unit','MM');doc=TDocStd_Document(TCollection_ExtendedString('cad'));r=STEPCAFControl_Reader();r.SetNameMode(True);assert r.ReadFile(str(source))==IFSelect_RetDone;assert r.Transfer(doc);st=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main());roots=Sequence_TDF_Label();st.GetFreeShapes(roots)
 def compound(shapes):
  result=TopoDS_Compound();b=BRep_Builder();b.MakeCompound(result)
  for shape in shapes:b.Add(result,shape)
  return result
 original=compound([st.GetShape_s(roots.Value(i)) for i in range(1,roots.Length()+1)])
 def collect(exclude):
  shapes=[];removed=[]
  def walk(label,loc):
   name=label_name(label)
   if exclude and name in names:removed.append(name);return
   if st.IsReference_s(label):
    referred=TDF_Label();assert st.GetReferredShape_s(label,referred);walk(referred,loc.Multiplied(st.GetLocation_s(label)))
   elif st.IsAssembly_s(label):
    children=Sequence_TDF_Label();st.GetComponents_s(label,children,False)
    for i in range(1,children.Length()+1):walk(children.Value(i),loc)
   else:shapes.append(st.GetShape_s(label).Moved(loc))
  for i in range(1,roots.Length()+1):walk(roots.Value(i),TopLoc_Location())
  return compound(shapes),removed,len(shapes)
 whole,_,whole_parts=collect(False);assert max(abs(a-b) for a,b in zip(bounds(whole),bounds(original)))<1e-5
 original_volume=volume(original);assert abs(volume(whole)-original_volume)<max(1e-5,abs(original_volume)*1e-7)
 result,removed,kept_parts=collect(True);assert len(removed)==1,removed;assert volume(result)>0 and original_volume-volume(result)>0
 writer=STEPControl_Writer();assert writer.Transfer(result,STEPControl_AsIs)==IFSelect_RetDone;assert writer.Write(str(target))==IFSelect_RetDone
 return {'removed_named_assemblies':removed,'whole_leaf_count':whole_parts,'kept_leaf_count':kept_parts,'original_bounds_mm':bounds(original),'result_bounds_mm':bounds(result),'original_volume_mm3':original_volume,'result_volume_mm3':volume(result),'validation':'Unfiltered reconstructed assembly matches original world bounds and volume; all retained source component placements preserved.'}

"""Extend a simple labelled bar CAD without scaling holes or width."""
import math,shutil
from pathlib import Path
import ezdxf
from ezdxf import bbox

def extend_bar(file,target_length_mm):
 file=Path(file);original=file.with_name(file.stem+'_source.dxf');shutil.copy2(file,original)
 doc=ezdxf.readfile(file);ms=doc.modelspace();ext=bbox.extents(ms)
 circles=list(ms.query('CIRCLE'));outlines=list(ms.query('LWPOLYLINE'))
 assert len(outlines)==1 and len(circles)+1==len(ms),'Only reviewed simple bar geometry may be extended'
 old=ext.size.y;width=ext.size.x;assert target_length_mm>=old
 small=min(e.dxf.radius for e in circles)
 taps=sorted([e for e in circles if abs(e.dxf.radius-small)<1e-5],key=lambda e:e.dxf.center.y)
 pitch=taps[1].dxf.center.y-taps[0].dxf.center.y
 assert all(abs((b.dxf.center.y-a.dxf.center.y)-pitch)<1e-5 for a,b in zip(taps,taps[1:]))
 edge_gap=old/2-max(abs(e.dxf.center.y) for e in taps)
 count=math.floor((target_length_mm-2*edge_gap)/pitch)+1
 # Preserve the original symmetric even-hole arrangement.
 if count%2:count-=1
 attributes=taps[0].dxfattribs();attributes.pop('handle',None);attributes.pop('owner',None);attributes.pop('center',None);attributes.pop('radius',None)
 ends=[e for e in circles if abs(e.dxf.radius-small)>=1e-5]
 for e in taps:ms.delete_entity(e)
 for i in range(count):ms.add_circle((0,(i-(count-1)/2)*pitch),small,dxfattribs=attributes)
 delta=(target_length_mm-old)/2
 for e in ends:
  center=e.dxf.center;e.dxf.center=(center.x,center.y+(delta if center.y>0 else -delta),center.z)
 outlines[0].set_points([(-width/2,-target_length_mm/2),(width/2,-target_length_mm/2),(width/2,target_length_mm/2),(-width/2,target_length_mm/2)])
 doc.saveas(file)
 assert abs(bbox.extents(ms).size.y-target_length_mm)<1e-5
 assert not doc.audit().has_errors
 return {'source_file':original.name,'source_length_mm':round(old,3),'length_mm':target_length_mm,'width_mm':round(width,3),'hole_diameter_mm':small*2,'pitch_mm':round(pitch,3),'repeated_holes':count,'end_holes_preserved':4,'method':'Extend body; move original end holes; repeat centre holes at original pitch; no nonuniform scale','status':'CAD gia công biến thể theo yêu cầu, chưa xác nhận vật liệu/chiều dày/dòng/cọc đấu'}

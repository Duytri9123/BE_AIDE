"""Recover isolated manufacturer vector drawings in dimension-verified mm.

Only PDF path geometry is used, never OCR, photos or invented device details.
The caller supplies a visually reviewed drawing window and one dimension anchor;
a second independent extent must be checked before publishing the resulting CAD.
"""
import math
from pathlib import Path
import ezdxf
import pymupdf


def _bezier(points,tolerance):
 a,b,c,d=points
 def dist(p):
  dx,dy=d[0]-a[0],d[1]-a[1]
  return abs(dy*p[0]-dx*p[1]+d[0]*a[1]-d[1]*a[0])/max(math.hypot(dx,dy),1e-12)
 if max(dist(b),dist(c))<=tolerance:return [a,d]
 mid=lambda x,y:((x[0]+y[0])/2,(x[1]+y[1])/2)
 ab,bc,cd=mid(a,b),mid(b,c),mid(c,d);abc,bcd=mid(ab,bc),mid(bc,cd);m=mid(abc,bcd)
 return _bezier((a,ab,abc,m),tolerance)[:-1]+_bezier((m,bcd,cd,d),tolerance)


def vector_view(pdf,page_number,window,anchor_mm,target,angle=0,anchor_axis='x',physical_height_mm=None):
 doc=pymupdf.open(pdf);page=doc[page_number-1];box=pymupdf.Rect(window);paths=[]
 for drawing in page.get_drawings():
  # Ignore transparent clipping paths; only source-visible paths are drawings.
  if drawing.get('stroke_opacity',1)==0 and drawing.get('fill_opacity',1)==0:continue
  for item in drawing['items']:
   kind=item[0]
   if kind=='l':points=[tuple(item[1]),tuple(item[2])]
   elif kind=='c':points=[tuple(p) for p in item[1:5]]
   elif kind=='re':
    r=item[1];points=[tuple(r.tl),tuple(r.tr),tuple(r.br),tuple(r.bl),tuple(r.tl)]
   elif kind=='qu':points=[tuple(item[1].ul),tuple(item[1].ur),tuple(item[1].lr),tuple(item[1].ll),tuple(item[1].ul)]
   else:raise ValueError('Unsupported source PDF primitive: '+kind)
   if all(box.contains(pymupdf.Point(p)) for p in points):paths.append((kind,points))
 assert paths,(pdf,page_number,window)
 all_points=[p for _,points in paths for p in points]
 lo=[min(p[a] for p in all_points) for a in (0,1)];hi=[max(p[a] for p in all_points) for a in (0,1)]
 scale=anchor_mm/(hi[0]-lo[0] if anchor_axis=='x' else hi[1]-lo[1])
 scale_y=physical_height_mm/(hi[1]-lo[1]) if physical_height_mm is not None else scale
 out=ezdxf.new('R2010');out.units=4;model=out.modelspace();theta=math.radians(angle)
 def convert(p):
  x,y=(p[0]-lo[0])*scale,(hi[1]-p[1])*scale_y
  return x*math.cos(theta)-y*math.sin(theta),x*math.sin(theta)+y*math.cos(theta)
 for kind,points in paths:
  points=_bezier(points,.005/max(scale,scale_y)) if kind=='c' else points
  model.add_lwpolyline([convert(p) for p in points])
 assert not out.audit().errors
 target=Path(target);target.parent.mkdir(parents=True,exist_ok=True);out.saveas(target)
 return {'pdf_page':page_number,'source_window_pdf_points':list(window),'pdf_point_to_mm_scale_x':scale,'pdf_point_to_mm_scale_y':scale_y,
  'calibration':'Catalogue vector illustration calibrated to independently printed width and height; schematic details are references, not manufacturing coordinates.' if physical_height_mm is not None else 'Uniform dimension-anchor calibration',
  'anchor_dimension_mm':anchor_mm,'anchor_axis':anchor_axis,'rotation_degrees':angle,
  'curve_chord_tolerance_mm':.005,'source_path_primitives':len(paths),
  'recovered_extent_mm':[(hi[0]-lo[0])*scale,(hi[1]-lo[1])*scale_y]}

"""Join degree-two projected LINE chains without dropping branches or changing silhouettes."""
import collections,math
import ezdxf

def compact_lines(doc):
 lines=[];others=[];adj=collections.defaultdict(list)
 def key(p):return (round(p[0],7),round(p[1],7))
 for e in doc.modelspace():
  if e.dxftype()!='LINE':others.append(e);continue
  a=(e.dxf.start.x,e.dxf.start.y);b=(e.dxf.end.x,e.dxf.end.y)
  if key(a)==key(b):others.append(e);continue
  i=len(lines);lines.append((a,b));adj[key(a)].append(i);adj[key(b)].append(i)
 used=set();out=ezdxf.new('R2010');out.units=4;m=out.modelspace()
 def walk(i,start):
  pts=[start];node=key(start)
  while i not in used:
   used.add(i);a,b=lines[i];end=b if key(a)==node else a;pts.append(end);node=key(end)
   if len(adj[node])!=2:break
   nxt=[j for j in adj[node] if j not in used]
   if not nxt:break
   i=nxt[0]
  if len(pts)==2:m.add_line(*pts)
  else:m.add_lwpolyline(pts)
 for i,(a,b) in enumerate(lines):
  if i in used:continue
  if len(adj[key(a)])!=2:walk(i,a)
  elif len(adj[key(b)])!=2:walk(i,b)
 for i,(a,b) in enumerate(lines):
  if i not in used:walk(i,a)
 assert len(used)==len(lines)
 for e in others:
  q=e.copy();q.doc=None;m.add_entity(q)
 return out
if __name__=='__main__':
 import sys
 from pathlib import Path
 from ezdxf import bbox
 for arg in sys.argv[1:]:
  p=Path(arg);d=ezdxf.readfile(p);b=bbox.extents(d.modelspace());q=compact_lines(d);c=bbox.extents(q.modelspace());assert all(abs(x-y)<1e-5 for x,y in zip((*b.extmin,*b.extmax),(*c.extmin,*c.extmax)));assert not q.audit().errors
  tmp=p.with_suffix('.compact.dxf');q.saveas(tmp);tmp.replace(p);print(p.name,len(d.modelspace()),'->',len(q.modelspace()),flush=True)


def source_segment_count(entities):
 """Count real polyline edges, so compaction cannot make a valid face look empty."""
 return sum(max(0,len(e)-1)+int(e.closed) if e.dxftype()=='LWPOLYLINE' else 1 for e in entities)

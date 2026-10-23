import sys
sys.path.insert(0,'scripts')
from ls_projection_compaction import compact_lines
import unittest,ezdxf,math
from ezdxf import bbox
class ProjectionCompactionTests(unittest.TestCase):
 def test_closed_outline_and_branch_are_preserved(self):
  d=ezdxf.new();d.units=4;m=d.modelspace()
  for a,b in [((0,0),(5,0)),((5,0),(10,0)),((10,0),(10,10)),((10,10),(0,10)),((0,10),(0,0)),((5,0),(5,-3))]:m.add_line(a,b)
  q=compact_lines(d);before=bbox.extents(m);after=bbox.extents(q.modelspace());self.assertEqual(before.extmin,after.extmin);self.assertEqual(before.extmax,after.extmax)
  def segments(doc):
   result=[]
   for e in doc.modelspace():
    if e.dxftype()=='LINE':result.append((tuple(e.dxf.start)[:2],tuple(e.dxf.end)[:2]))
    else:
     points=[tuple(p)[:2] for p in e.get_points()];result.extend(zip(points,points[1:]))
   return result
  self.assertAlmostEqual(sum(math.dist(a,b) for a,b in segments(d)),sum(math.dist(a,b) for a,b in segments(q)))
  self.assertTrue(any((5,-3) in (a,b) for a,b in segments(q)))
 def test_three_closed_source_contours_remain_valid_after_compaction(self):
  from ls_projection_compaction import source_segment_count
  d=ezdxf.new();d.units=4
  for x in [0,20,40]:
   pts=[(x,0),(x+10,0),(x+10,10),(x,10),(x,0)]
   for a,b in zip(pts,pts[1:]):d.modelspace().add_line(a,b)
  q=compact_lines(d)
  self.assertEqual(len(q.modelspace()),3)
  self.assertEqual(source_segment_count(q.modelspace()),12)
  self.assertEqual(source_segment_count(q.modelspace()),source_segment_count(d.modelspace()))
if __name__=='__main__':unittest.main()

"""LS branch breaker references from the manufacturer dimension plates."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.complete_ls_remaining_geometry import BASE,outline
from scripts.supplement_ls_pricebook_20261106 import main as publish

def jobs():
 p=BASE/'BRANCH-KO.pdf';result=[]
 # Windows are in PDF points, not pixels. Each front is drawn independently.
 for key,model,page,w,h,depth,front,side in [
  ('32KGRd','32KGRd',33,35,80,79.5,(80,280,129,391),(224,280,331,391)),
  ('BS32c-BARE','BS32c (không vỏ)',33,33,70,59.2,(81,514,139,638),(220,514,321,638)),
  ('32GRc','32GRc',34,62,82,59.2,(71,262,148,365),(232,262,305,365)),
  ('32GRhS','32GRhS',34,32,70,55.6,(93,462,136,554),(233,462,312,554)),
  ('EBS52Fb','EBS52Fb',37,50,96,75.5,(105,309,143,377),(362,309,420,377)),
  ('EBE102Fb','EBE102Fb',38,75,96,75.5,(91,296,147,369),(370,296,427,369))]:
  restriction=f'Manufacturer industrial branch catalogue page {page} explicitly names {model.split(" (")[0]} and illustrates its correct pole/front family. The nominal body envelope is {w}×{h} mm; the side operating envelope is {depth} mm, including the handle projection where shown. Calibrated catalogue art is schematic; terminal-tab/rail-latch details and optional covers do not become fabrication coordinates. No BS leakage rating is inferred from an unrelated table and no GRc/GRh case is substituted. Electrical price-row settings remain unchanged.'
  result.append((key,[model],'2P',[w,h,depth],
   [('FRONT',page,front,w,h),('SIDE',page,side,depth,h)],p,restriction,
   {'name':'LS '+model,'require_whole_paths':False,'mounting_type':'Ray DIN hoặc bắt vít theo bản vẽ hãng'}))
 # A cover is an extra item. Only documented bare-body installation space can
 # be supplied until a dimensioned terminal-cover drawing is available.
 f=outline('BS32c-covered-common-body',33,70)
 result.append(('BS32c-COVERED-BODY',['BS32c w/c (có vỏ)'],'2P',[33,70],
  [('MOUNTING',33,None,33,70,f)],p,
  'Manufacturer BS32c drawing page 33 verifies the shared 33×70 mm base body. The quote adds a cover (w/c), which has no verified standalone external envelope in this sheet. This option contains only the shared base-body installation envelope: it excludes the cover and cannot establish the complete covered clearance or covered front appearance. The cover remains part of the original quote, not silently removed.',
  {'name':'LS BS32c có vỏ · tham chiếu thân cơ sở','geometry_representation':'Documented shared bare-body envelope; optional cover geometry not supplied','mounting_type':'Kiểm tra thêm khoảng hở vỏ che khi lắp'}))
 return result

if __name__=='__main__':publish(jobs(),report_name='ls_branch_geometry_review.json')

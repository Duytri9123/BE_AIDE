"""Mechanically reviewed LS references for the remaining October price rows."""
import sys
from pathlib import Path
import ezdxf
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.supplement_ls_pricebook_20261106 import main as publish,ROWS,CAT
BASE=CAT/'LS/NguonBenNgoai/REMAINING-20261106'

def outline(name,w,h,pitch=None):
 p=BASE/(name+'.dxf');d=ezdxf.new('R2010');d.units=4;m=d.modelspace()
 m.add_lwpolyline([(0,0),(w,0),(w,h),(0,h)],close=True)
 if pitch:
  px,py=pitch
  for x in ((w-px)/2,(w+px)/2):
   for y in ((h-py)/2,(h+py)/2):m.add_line((x-1.5,y),(x+1.5,y));m.add_line((x,y-1.5),(x,y+1.5))
 d.saveas(p);return p

def jobs():
 result=[];p=BASE/'SPD.pdf'
 windows=[(211,174,241,313),(258,174,315,313),(332,174,415,313),(432,174,543,313)]
 for poles in range(1,5):
  models=[r['sku'] for r in ROWS if r['category']=='SPD' and r['sku'].startswith(('BK10S','BK20S','BK30S','BK40S')) and r['sku'].endswith(f' {poles}P')]
  result.append((f'BK10-40S-{poles}P',models,f'{poles}P',[18*poles,90,69.5],
   [('FRONT',5,windows[poles-1],18*poles,90),('SIDE',5,(70,174,178,313),69.5,90)],p,
   'Manufacturer BK catalogue page 5 explicitly groups BK10S/20S/30S/40S-T2 and separately illustrates 1/2/3/4 poles with 18/36/54/72 mm widths, 90 mm height and 69.5 mm depth. Use the actual illustrated pole front, not a repeated module or a wrongly named distributor TS250 drawing. Printed dimensions calibrate schematic artwork only. Electrical surge ratings remain the user price-row values; no automatic insertion or fabrication approval.',
   {'name':'LS '+ ' / '.join(models),'mounting_type':'Ray DIN 35 mm'}))
 model=next(r['sku'] for r in ROWS if r['sku'].startswith('GIMAC-115P'))
 result.append(('GIMAC-115P',[model],None,[190,255,116],
  [('FRONT',169,(130,201,249,359),190,255),('SIDE',169,(354,201,428,359),116,255),('REAR',169,(130,404,249,563),190,255)],BASE/'GIMAC.pdf',
  'Manufacturer GIMAC-115P dimension/ordering page O-4-9 independently identifies the 190×255×116 mm body. Communications, CT current, frequency and auxiliary supply are electrical options of this body, not reasons to reject mechanically compatible projections. Correct rear and panel-mounted body reviewed; no GIMAC-1000 enclosure substitution or transferred ratings.',
  {'name':'LS GIMAC-115P','mounting_type':'Lắp trên cánh tủ'}))
 # Direct/extended handles have standalone, dimensioned front plates. The
 # catalogue side illustrations also contain a breaker; do not publish those
 # assemblies as the accessory itself.
 susol=CAT/'LS/NguonBenNgoai/SUSOL-CATALOG-202006/source.pdf'
 # These front-plate pitches are independently printed on the DH/EH sheets;
 # the plate envelope is only a mounting reference, not a fabricated handle.
 for kind in ('DH','EH'):
  for frame in range(1,5):
   model=next(r['sku'] for r in ROWS if r['sku'].startswith(f'{kind}{frame} '))
   page=(250 if kind=='DH' else 256)+frame
   width,height=[(90,81.3),(105,91.8),(140,147.5),(210,186.6)][frame-1]
   target=outline(f'{kind}{frame}-front-mount',width,height)
   result.append((f'{kind}{frame}-MOUNTING',[model],None,[width,height],
    [('MOUNTING',page,None,width,height,target)],susol,
    f'Manufacturer {kind}{frame} sheet and dimension table give the standalone front plate {width}×{height} mm. Publish only the documented front-plate envelope; upper/lower hole pitches differ and are deliberately not represented as a rectangular hole pattern. The breaker in the installation/side drawing is not part of this accessory CAD. No unsupported handle mechanism, corner radius, slot or enclosure is invented.',
    {'name':f'LS {kind}{frame} · bao hình đế tay xoay','geometry_representation':'Documented dimension-based accessory mounting outline','mounting_type':'Theo tâm gá trên bản vẽ hãng'}))
 # Motor operator front-plate dimensions A1/B1/B3 are explicit in the
 # manufacturer's table. 3- and 4-pole parent covers are separate options.
 p=BASE/'METASOL-CATALOG.pdf'
 for i,height,width3,width4 in [(1,110.5,75,100),(2,132,90,120),(3,126,105,140),(4,215,140,184),(5,243,210,280),(6,322.5,220,289)]:
  model=next(r['sku'] for r in ROWS if r['sku'].startswith(f'MOP M{i} '))
  for host,width in [(3,width3),(4,width4)]:
   target=outline(f'MOP-M{i}-host{host}-front',width,height)
   result.append((f'MOP-M{i}-HOST{host}',[model],None,[width,height],
    [('MOUNTING',141,None,width,height,target)],p,
    f'Manufacturer remote-operation dimension table 9-31 defines MOP-M{i} A1={height} mm, B1={width3} mm for the three-pole cover and B3={width4} mm for the four-pole cover. A1 is the operator front-plate height, not total breaker height. This is the documented accessory front envelope only: no breaker poles, terminals, unsupported fasteners, or whole-breaker outline are copied. Parent pole configuration must be selected; the price row covers a family and does not approve an exact order variant.',
    {'name':f'LS MOP-M{i} · bao hình cho MCCB '+('ba cực' if host==3 else 'bốn cực'),
     'geometry_representation':'Documented dimension-based accessory front envelope','extra_spec':{'Số cực thiết bị ghép':f'{host}P'},
     'view_labels':{'MOUNTING':f'Mặt đế gá theo bản vẽ · cho MCCB {host}P'},'mounting_type':'Ghép MCCB thuộc khung tương thích'}))
 # Adjustable trip models have dedicated manufacturer FMU drawings.
 p=BASE/'FMU.pdf'
 for frame,page,height,fronts,depth,side in [
  (1,36,155,[(3,90,(106.5,277,174,392)),(4,120,(285,277,374,392))],82,(468,277,530,392)),
  (2,37,165,[(3,105,(94,270,167,387)),(4,140,(261,270,359,387))],86.85,(462,270,525,387))]:
  for poles,width,window in fronts:
   model=next(r['sku'] for r in ROWS if r['sku']==f'ABS{frame}0{poles}c FMU')
   result.append((f'ABS{frame}0{poles}c-FMU',[model],f'{poles}P',[width,height,depth],
    [('FRONT',page,window,width,height),('SIDE',page,side,depth,height)],p,
    f'Dedicated manufacturer adjustable-trip ABS-FMU catalogue page {page} illustrates the correct {poles}-pole ABS{frame}25c/250c frame. Crop the breaker body, excluding optional insulation barriers, terminal-extension busbars, callouts and adjacent pole illustrations. Calibrate the manufacturer drawing to its printed body dimensions. The FMU setting remains the price row electrical option. No fixed-trip front substitution or fabrication approval.',
    {'name':f'LS ABS{frame}0{poles}c FMU','require_whole_paths':False,'mounting_type':'Bắt vít lên tấm gá'}))
 return result

if __name__=='__main__':publish(jobs(),report_name='ls_remaining_geometry_review.json')

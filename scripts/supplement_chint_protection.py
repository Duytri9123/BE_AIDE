"""Complete mechanically reviewed CHINT breaker/overload reference views."""
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.supplement_chint_catalog_views import recovered,metadata,BASE
from scripts.supplement_chint_control import existing_job
from scripts import supplement_chint_native2d as writer


def jobs():
 result=[];p=BASE/'NXB-125/source.pdf'
 for poles,depth in ((1,75.5),(2,78.5),(3,78.5)):
  ids=[f'chint-dika-2026-06:2:1:{line}:{poles+4}' for line in (3,4)]
  views=[('SIDE',9,(320,484,413,585),depth,80.5,0)]
  if poles==2:views.insert(0,('FRONT',9,(228,484,293,585),54,80.5,0))
  job=recovered(f'NXB-125-{poles}P',['NXB-125'],ids,p,views,
   f'CHINT NXB-125 · {poles}P',f'{poles}P',{'Kiểu lắp':'Ray DIN TH35-7.5'})
  job['size']=[27*poles,80.5,depth]
  job['restriction']+=' Manufacturer page 9 explicitly gives 27/54/81 mm pole widths and 75.5 mm unipolar / 78.5 mm multipolar depth. Publish the common side profile for 1P/3P; only the actually illustrated 2P front is used. Do not copy two front terminals into a 1P or 3P drawing.'
  result.append(job)
 p=ROOT/'data/CatalogTB/Chint/NguonBenNgoai/PRIMARY-RECHECK-20261023/NXR-CATALOG/source.pdf'
 result.append(recovered('NXR-25',['NXR-25'],['chint-dika-2026-06:5:0:2:6'],p,
  [('FRONT',6,(245,149,314,253),45,67,0)],'Rơ-le nhiệt CHINT NXR-25',spec={'Kiểu lắp':'Ghép contactor phù hợp'}))
 result.append(recovered('NXR-200',['NXR-200'],['chint-dika-2026-06:5:0:7:6'],p,
  [('FRONT',7,(258,120,371,239),128,134,0)],'Rơ-le nhiệt CHINT NXR-200',spec={'Kiểu lắp':'Ghép contactor phù hợp'}))
 job=recovered('NXR-630-630A-SIDE',['NXR-630'],['chint-dika-2026-06:5:0:9:6'],p,
  [('SIDE',7,(396,346,541,481),161.3,155,0)],'Rơ-le nhiệt CHINT NXR-630 · khung 630A',spec={'Kiểu lắp':'Gá vít độc lập trên tấm lắp','Bước đầu nối động lực (mm)':'55'})
 job['size']=[158.6,155,161.3]
 job['restriction']+=' Manufacturer page 7 documents a common side housing and two different terminal pitches: 48 mm for 400A, 55 mm for 630A. Publish only the side housing for this row, never the 400A front terminal pattern.'
 result.append(job)
 result.append(existing_job('OFFICIAL-NATIVE2D-SRC_CHINT_2f7527c08497',['NXM-1250H'],['chint-dika-2026-06:3:0:10:5'],[(0,'FRONT')],
  'https://www.chintglobal.com/global/en/products/low-voltage/iec/secondary-power-distribution/nxm.html',
  'Manufacturer NXM catalogue page 28 gives both 1250 and 1600 frames the same 3P front envelope, 210×370 mm (4P width is 280 mm). Existing source outline has exactly three terminal groups at each end and measures 210×370 mm. The 1600H source block is accepted as compatible 1250H front geometry; no current or release rating is transferred.',
  'MCCB CHINT NXM-1250H · 3P · mặt trước','3P',{'Kiểu lắp':'Gá vít trên tấm lắp'}))
 return result


if __name__=='__main__':writer.main(jobs(),report_name='chint_protection_cad_review.json',reviewed_on='2026-11-06')

"""Reviewed socket, protection-relay and fuse catalogue geometry."""
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.supplement_chint_catalog_views import BASE,recovered,make_job,metadata,rectangle
from scripts import supplement_chint_native2d as writer


def jobs():
 result=[];p=BASE/'CZY-EU/source.pdf'
 for key,line,y0,y1 in [('CZY08B-01',8,228,311),('CZY14B',9,546,630)]:
  job=recovered(key,[key],[f'chint-dika-2026-06:6:1:{line}:5'],p,
   [('FRONT',1,(336,y0,376,y1),30.5,63,0),('SIDE',1,(399,y0,437,y1),26,63,0)],
   'Đế rơ-le CHINT '+key,spec={'Kiểu lắp':'Ray DIN hoặc gá vít theo bản vẽ'})
  job['size']=[30.5,63,26];result.append(job)
 p=BASE/'SOCKET-LEGACY/source.pdf'
 job=recovered('CZF08A',['CZF08A'],['chint-dika-2026-06:6:1:11:5'],p,
  [('FRONT',121,(84,270,135,335),41,52,0),('SIDE',121,(154,270,183,335),21.5,52,0)],
  'Đế rơ-le CHINT CZF08A',spec={'Kiểu lắp':'Ray DIN hoặc gá vít theo bản vẽ'})
 job['size']=[41,52,21.5];result.append(job)
 job=recovered('XJ3-D',['XJ3-D'],['chint-dika-2026-06:7:1:3:6'],p,
  [('FRONT',42,(61,704,107,769),45.5,70.5,0),('SIDE',42,(146,715,241,778),115,70.5,0)],
  'Rơ-le bảo vệ CHINT XJ3-D',spec={'Kiểu lắp':'Ray DIN 35 mm hoặc gá vít'})
 job['size']=[45.5,70.5,115]
 job['restriction']+=' The XJ3-D drawing is independently labelled and dimensioned on manufacturer page I-40. Do not reuse the taller XJ3-G/S body.'
 result.append(job)
 p=BASE/'AC30/source.pdf'
 source=metadata(p);source['pdf_pages']=[1]
 target=rectangle(p.parent/'AC30-103-envelope.dxf',18,80)
 job=make_job('AC30-103',['AC30-103'],['chint-dika-2026-06:10:0:6:11'],source,
  [('FRONT',None,0,[18,80],target)],[18,80],
  'The CHINT-authored AC30 diagram in the upper half of the engineering sheet explicitly dimensions the two-pin 103 front at 18×80 mm. Only this dimension-based envelope is published. The PDF also contains occluded/clipped path primitives from other aperture variants, which are excluded rather than copied into the 103 socket. Lower-half drawings of another manufacturer are excluded.',
  'Ổ cắm ray DIN CHINT AC30-103 · bao hình mặt trước',spec={'Kiểu lắp':'Ray DIN 35 mm'})
 result.append(job)
 p=BASE/'RT28/source.pdf'
 job=recovered('RT28N-32X-1P',['RT28N-32X/1P'],['chint-dika-2026-06:10:0:30:11'],p,
  [('FRONT',2,(252,579,276,656),18,81,0),('SIDE',2,(69,567,177,654),81,61,90)],
  'Đế cầu chì CHINT RT28N-32X · 1P','1P',{'Kiểu lắp':'Ray DIN TH35-7.5'})
 job['size']=[18,81,61]
 job['restriction']+=' Manufacturer table 4.1 specifies the single-pole 18 mm width, 81 mm height and 61 mm maximum depth. The side illustration is rotated to its DIN-rail mounting pose. The signal window remains schematic; no 2P/3P terminals are substituted.'
 result.append(job)
 job=recovered('RT28-32',['RT28-32'],['chint-dika-2026-06:10:0:31:11'],p,
  [('FRONT',2,(359,583,382,661),10.3,38,0)],'Ruột cầu chì CHINT RT28-32',
  spec={'Kiểu lắp':'Lắp trong đế cầu chì tương thích 10×38 mm'})
 job['restriction']+=' Table 4.2 identifies the nominal 10×38 mm fuse link; the drawing and table 4.1 give cap diameter G=10.3±0.1 and length K=38±0.6 mm. No electrical current rating is taken from the drawing.'
 result.append(job)
 return result


if __name__=='__main__':writer.main(jobs(),report_name='chint_socket_cad_review.json',reviewed_on='2026-11-06')

import os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'data/CatalogTB/BienDong/ABB/NguonBenNgoai'
CORE=Path('C:/Program Files/Autodesk/AutoCAD 2022/accoreconsole.exe')
for dwg in sorted(ROOT.glob('*/*.dwg')):
 dxf=dwg.with_suffix('.dxf')
 if dxf.exists():continue
 script=dwg.parent/'convert.scr'
 script.write_text('FILEDIA\n0\nSECURELOAD\n2\n_.DXFOUT\n'+dxf.as_posix()+'\n_Version\n2018\n16\n_.QUIT\n_Y\n',encoding='ascii')
 with (dwg.parent/'conversion.log').open('wb') as log:
  result=subprocess.run([str(CORE),'/i',str(dwg),'/s',str(script),'/l','en-US'],stdout=log,stderr=log,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
 if not dxf.exists():raise RuntimeError('Failed to convert '+dwg.name)
 print(dwg.stem, dxf.stat().st_size,flush=True)

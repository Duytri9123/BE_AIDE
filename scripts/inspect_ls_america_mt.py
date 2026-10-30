"""Render source STEP projections before assigning equipment view roles."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from ezdxf import bbox
from ezdxf.addons.drawing import matplotlib
from PIL import Image, ImageOps, ImageDraw
from ls_native_writer import CAT, ROOT

out = ROOT/'docs/ls-all-cad-2026-10-24/research-2026-10-25'
out.mkdir(exist_ok=True)
canvas = Image.new('RGB', (1800, 1200), 'white')
draw = ImageDraw.Draw(canvas)
for row, ident in enumerate(sys.argv[1:] or ['33178','23731','33175','22404']):
    for col, code in enumerate(['FRONT','REAR','SIDE-L','SIDE','TOP','BOTTOM']):
        folder=ident if '/' in ident else 'AMERICA-'+ident
        doc = ezdxf.readfile(CAT/'LS/NguonBenNgoai'/folder/('hlr-poly-'+code+'.dxf'))
        path = out/f'{ident.replace("/","-")}-{code}.png'
        matplotlib.qsave(doc.modelspace(),path,dpi=65)
        im = ImageOps.contain(Image.open(path).convert('RGB'), (290,260))
        x,y = col*300,row*300
        canvas.paste(im,(x+(300-im.width)//2,y+30))
        size=bbox.extents(doc.modelspace()).size
        draw.text((x+5,y+5),f'{ident} {code} {size.x:.1f} x {size.y:.1f}',fill='black')
canvas.save(out/'mt-source-projections.png')

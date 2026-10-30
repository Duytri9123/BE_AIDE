"""Render isolated, source-coordinate review candidates from the DC column."""
import json,collections
from ls_native_writer import ROOT,CAT
import ezdxf
from ezdxf import bbox
from ezdxf.addons.drawing import matplotlib
SOURCE=CAT/'LS/NguonBenNgoai/RU-660d12651a0f0c18'
OUT=ROOT/'docs/ls-targeted-review-2026-10-26';OUT.mkdir(exist_ok=True)
WINDOWS={
 'MC6-18':(-2700,-800,-2110,-600),
 'MC50-65':(-2700,-1490,-2110,-1250),
 'MC75-100':(-2700,-1800,-2110,-1510),
 'MC130-150':(-2700,-2220,-1750,-1820),
}

def main():
    doc=ezdxf.readfile(SOURCE/'source.dxf');cache=bbox.Cache();geometry=[]
    for e in doc.modelspace():
        if e.dxftype() not in {'LINE','ARC','CIRCLE','SPLINE','ELLIPSE','LWPOLYLINE','POLYLINE'}:continue
        b=bbox.extents([e],cache=cache)
        if b.has_data:geometry.append((e,b))
    report=[]
    for name,(x,y,X,Y) in WINDOWS.items():
        es=[e for e,b in geometry if b.extmin.x>=x and b.extmax.x<=X and b.extmin.y>=y and b.extmax.y<=Y]
        d=ezdxf.new();d.units=4
        from ezdxf.addons import Importer
        imp=Importer(doc,d);imp.import_entities(es);imp.finalize()
        d.saveas(OUT/(name+'-window.dxf'));matplotlib.qsave(d.modelspace(),OUT/(name+'-window.png'),dpi=150)
        layers=collections.Counter(e.dxf.layer for e in es)
        report.append(dict(model=name,window=[x,y,X,Y],layers=dict(layers),entities=len(es)))
    (OUT/'dc-window-review.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(report,flush=True)

if __name__=='__main__':main()

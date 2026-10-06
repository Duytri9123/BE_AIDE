"""Render original native DXF with CAD background masks transparent in preview.

The editable DXF/DWG files are never changed. Some AutoCAD WIPEOUT entities
are exported as background-colour SVG fills that cover the device linework.
"""
import re
import sys
from pathlib import Path

import cairosvg
import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext, config, layout, svg

ROOT=Path(__file__).resolve().parents[2]
CAT=ROOT/'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
for arg in sys.argv[1:]:
    source=CAT/arg
    assert source.is_file() and source.suffix.lower()=='.dxf',source
    drawing=ezdxf.readfile(source)
    backend=svg.SVGBackend()
    cfg=config.Configuration(background_policy=config.BackgroundPolicy.CUSTOM,
                             custom_bg_color='#202830')
    Frontend(RenderContext(drawing),backend,config=cfg).draw_layout(
        drawing.modelspace(),finalize=True)
    markup=backend.get_string(layout.Page(180,180,layout.Units.mm,
                                          margins=layout.Margins.all(5)))
    # Change only SVG paint for background-colour mask classes. All linework
    # and source entities remain intact in the saved CAD files.
    markup=re.sub(r'(\.C\d+ \{[^}]*?fill: )#202830(; fill-opacity: )1\.000',
                  r'\1none\g<2>0.000',markup)
    image=source.with_name(source.stem+'-verified.png')
    cairosvg.svg2png(bytestring=markup.encode(),write_to=str(image),
                     output_width=900)
    print(image.relative_to(CAT),flush=True)

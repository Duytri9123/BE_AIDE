"""Render a CAD overview or true zoom using relative source viewports."""
import hashlib
import json
import threading
from pathlib import Path
from app.services.ingestion.cad_source_evidence import cad_evidence

_RENDER_LOCK=threading.RLock()


def render_schematic_source(file_path, region=None):
    import ezdxf
    from ezdxf import bbox, select
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from ezdxf.addons.drawing.config import Configuration, ColorPolicy, BackgroundPolicy
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    source=Path(file_path)
    evidence=cad_evidence(source,region)
    bounds=evidence.get('view_bounds')
    if not bounds:return None
    key=hashlib.sha256(json.dumps(region).encode()).hexdigest()[:12]
    output=source.parent/'.cad-analysis'/(source.stem+'-sld-v8-'+key+'.png')
    if output.is_file() and output.stat().st_mtime_ns>=source.stat().st_mtime_ns:return str(output)
    left,bottom,right,top=bounds
    width=max(right-left,1);height=max(top-bottom,1)
    with _RENDER_LOCK:
        doc=ezdxf.readfile(source)
        fig=Figure(figsize=(20*width/max(width,height),20*height/max(width,height)),dpi=180)
        FigureCanvasAgg(fig);ax=fig.add_axes([0,0,1,1])
        config=Configuration(color_policy=ColorPolicy.BLACK,background_policy=BackgroundPolicy.WHITE,min_lineweight=1.0)
        layout=doc.modelspace()
        from app.services.ingestion.cad_viewports import overlapping_entities
        selected=overlapping_entities(doc,(left,bottom,right,top))
        handles={entity.dxf.handle for entity in selected}
        Frontend(RenderContext(doc),MatplotlibBackend(ax,adjust_figure=False),config=config).draw_layout(
            layout,finalize=True,filter_func=lambda entity: entity.dxf.handle in handles)
        ax.set_xlim(left,right);ax.set_ylim(bottom,top);ax.set_aspect('equal',adjustable='box');ax.axis('off')
        output.parent.mkdir(parents=True,exist_ok=True)
        temp=output.with_name(output.stem+'.tmp.png')
        fig.savefig(temp,dpi=180,facecolor='white');fig.clear();temp.replace(output)
    return str(output)

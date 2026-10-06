from build_tudien_library import *
import logging, copy
from ezdxf.addons.drawing import RenderContext,Frontend,svg,layout,config
from ezdxf.math import BoundingBox2d
logging.getLogger('ezdxf').setLevel(logging.ERROR)
for p in sorted((OUT/'nguon').glob('*/drawing.dxf')):
 dest=OUT/'form_tu'/p.parent.name/'overview.svg'
 if dest.with_name('preview_done_v2.json').exists():continue
 try:
  doc=ezdxf.readfile(p);backend=svg.SVGBackend()
  cfg=config.Configuration(background_policy=config.BackgroundPolicy.WHITE,color_policy=config.ColorPolicy.BLACK,text_policy=config.TextPolicy.IGNORE,hatch_policy=config.HatchPolicy.IGNORE)
  Frontend(RenderContext(doc),backend,config=cfg).draw_layout(doc.modelspace(),finalize=True)
  frames=[(e,bounds([e])) for e in doc.modelspace().query('INSERT') if 'KHUNG' in norm(e.dxf.name)]
  render_box=BoundingBox2d([point[:2] for _,b in frames if b for point in b]) if frames else None
  result=backend.get_string(layout.Page(420,297,layout.Units.mm,margins=layout.Margins.all(5)),render_box=render_box,settings=layout.Settings(crop_at_margins=True))
  dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(result,encoding='utf8');print(p.parent.name,flush=True)
  for e,b in frames:
   if b:
    f=dest.parent/'frames'/e.dxf.handle/'preview.svg';f.parent.mkdir(parents=True,exist_ok=True)
    points=[backend.transformation_matrix.transform((x,y,0)) for x in [b[0][0],b[1][0]] for y in [b[0][1],b[1][1]]]
    x=min(p.x for p in points);y=min(p.y for p in points);w=max(p.x for p in points)-x;h=max(p.y for p in points)-y
    f.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x} {y} {w} {h}" width="1200" height="{1200*h/w}"><image href="../../overview.svg" x="0" y="0" width="1000000" height="707143"/></svg>',encoding='utf8')
  save(dest.with_name('preview_done_v2.json'),{'frames':len(frames),'text_and_hatching':'omitted_in_preview_only'})
 except Exception as e:print(p.parent.name,str(e),flush=True)

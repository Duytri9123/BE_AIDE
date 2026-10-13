from pathlib import Path
import sys,json,csv,html
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tmp/tudien_deps"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import ezdxf
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf import bbox
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2];CAT=ROOT/"BE_AIDE/data/CatalogTB";OUT=ROOT/"outputs/catalogtb-84-evidence";OUT.mkdir(exist_ok=True)
rows=list(csv.DictReader((ROOT/"outputs/catalogtb-agent-audit/unresolved-identities.csv").open(encoding="utf-8-sig")));results=[]
for n,row in enumerate(rows,1):
 p=CAT/row["profile"];d=json.loads(p.read_text(encoding="utf8"));views=[]
 for k,v in enumerate(d.get("cad_don",[])):
  path=p.parent/v.get("duong_dan",f"CadDon/{v.get('id_hinh_goc')}/ban_ve.dxf")
  doc=ezdxf.readfile(path);texts=[]
  def visit(entities,depth=0):
   if depth>8:return
   for e in entities:
    if e.dxftype() in ("TEXT","MTEXT","ATTRIB","ATTDEF"):
     text=e.plain_text() if e.dxftype()=="MTEXT" else e.dxf.text
     if text.strip():texts.append(text.strip())
    if e.dxftype()=="INSERT":
     visit(e.attribs,depth+1)
     try:visit(e.virtual_entities(),depth+1)
     except Exception:pass
  visit(doc.modelspace());bounds=bbox.extents(doc.modelspace())
  image=OUT/f"{n:02d}-{k}.png";fig=plt.figure(figsize=(5,5),dpi=130);ax=fig.add_axes([0,0,1,1]);ax.set_facecolor("#202830")
  try:
   Frontend(RenderContext(doc),MatplotlibBackend(ax)).draw_layout(doc.modelspace(),finalize=True);fig.savefig(image,facecolor="#202830")
   error=None
  except Exception as ex:error=str(ex)
  plt.close(fig)
  views.append(dict(path=str(path.relative_to(CAT)),image=image.name,texts=list(dict.fromkeys(texts)),units=doc.units,bounds=[list(bounds.extmin),list(bounds.extmax)] if bounds.has_data else None,render_error=error,source_face=v.get("huong_nhin")))
 results.append(dict(number=n,**row,source_metadata=d,views=views));print(f"{n}/84",flush=True)
(OUT/"evidence.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf8")
for start in range(0,84,12):
 sheet=Image.new("RGB",(1200,1200),"white");draw=ImageDraw.Draw(sheet)
 for j,r in enumerate(results[start:start+12]):
  x=(j%4)*300;y=(j//4)*400
  im=Image.open(OUT/r["views"][0]["image"]).convert("RGB");im.thumbnail((290,330));sheet.paste(im,(x,y));draw.text((x+4,y+332),str(r["number"])+" "+r["name"].replace(" · CAD nguồn","")[:44],fill="black")
 sheet.save(OUT/f"sheet-{start//12+1}.jpg")
parts=['<!doctype html><meta charset="utf-8"><title>84 CAD: bằng chứng nhận diện</title><style>body{font:15px Arial;margin:24px}img{width:330px}article{border-bottom:1px solid #aaa;padding:15px}pre{white-space:pre-wrap}</style><h1>84 hồ sơ: hình CAD và chữ trích xuất</h1>']
for r in results:
 parts.append('<article><h2>'+str(r["number"])+'. '+html.escape(r["name"])+ '</h2><p>'+html.escape(r["profile"])+ '</p>')
 for v in r['views']:parts.append('<img src="'+v['image']+'"><pre>'+html.escape(json.dumps({k:v[k] for k in ('texts','units','bounds','source_face','render_error')},ensure_ascii=False,indent=2))+'</pre>')
 parts.append('</article>')
(OUT/'review.html').write_text('\n'.join(parts),encoding='utf8')

"""Validate MT views and refresh strict coverage with current source profiles."""
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ls_native_writer import CAT, ROOT
from ezdxf import bbox
import ezdxf
from PIL import Image,ImageOps,ImageDraw
OUT=ROOT/'docs/ls-all-cad-2026-10-24'

def main():
    additions=json.loads((OUT/'mt-america-additions-20261025.json').read_text(encoding='utf8'))
    canvas=Image.new('RGB',(1800,len(additions)*250),'white');draw=ImageDraw.Draw(canvas)
    validation=[]
    for row,item in enumerate(additions):
        p=CAT/item['profile'];profile=json.loads(p.read_text(encoding='utf8'))
        dimensions={}
        for col,v in enumerate(profile['cad_don']):
            path=p.parent/v['duong_dan'];doc=ezdxf.readfile(path);audit=doc.audit()
            assert doc.units==4 and not audit.errors and not audit.fixes
            ev=json.loads(path.with_name('evidence.json').read_text(encoding='utf8'))
            assert ev['step_sha256']==hashlib.sha256((CAT/item['source']/'source.step').read_bytes()).hexdigest()
            size=bbox.extents(doc.modelspace()).size;dimensions[v['huong_nhin']]=[size.x,size.y]
            validation.append(dict(model=item['model'],face=v['huong_nhin'],path=path.relative_to(CAT).as_posix(),
                                   sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                   width_mm=size.x,height_mm=size.y,entities=len(doc.modelspace()),
                                   audit_errors=0,audit_fixes=0))
            image=ImageOps.contain(Image.open(path.with_name('preview.png')).convert('RGB'),(290,215))
            x,y=col*300,row*250;canvas.paste(image,(x+(300-image.width)//2,y+28))
            draw.text((x+5,y+5),item['model']+' '+v['id_hinh_goc'].rsplit('-',1)[-1],fill='black')
        front=dimensions['Mặt trước'];rear=dimensions['Mặt sau'];side=dimensions['Mặt bên phải'];top=dimensions['Mặt trên']
        assert max(abs(a-b) for a,b in zip(front,rear))<.2
        assert abs(front[1]-side[1])<.2 and abs(front[0]-top[0])<.2 and abs(side[0]-top[1])<.2
    canvas.save(OUT/'mt-america-contact-sheet-20261025.png')
    (OUT/'mt-america-validation-20261025.json').write_text(json.dumps(validation,indent=2),encoding='utf8')
    from app.services.catalogtb_browser import _refresh_browser_data
    _refresh_browser_data(CAT)
    import audit_ls_pricebook_cad_coverage as audit
    audit.OUT=OUT;result=audit.main()
    from continue_ls_cad_coverage import reconcile
    reconcile(result)
    return result

if __name__=='__main__':main()

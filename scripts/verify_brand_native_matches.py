"""Check priced CAD links against native DXF poles and gallery states."""
import json
from html.parser import HTMLParser
from pathlib import Path

import ezdxf
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
CAT=ROOT/'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
folders=['SCHNEIDER_D01_DU_LIEU_MOI','ABB_D03_DU_LIEU_MOI',
         'SHIHLIN_D06_DU_LIEU_MOI']

class Options(HTMLParser):
    def __init__(self):
        super().__init__();self.ids=set()
    def handle_starttag(self,tag,attrs):
        if tag=='option': self.ids.add(dict(attrs).get('value'))

summary={}
for folder in folders:
    base=CAT/folder
    rows=json.loads((base/'price_index.json').read_text(encoding='utf8'))
    gallery=Options();gallery.feed((base/'cad_gallery.html').read_text(encoding='utf8'))
    checked={}
    for row in rows:
        if not row.get('cad_dwg'): continue
        state=row['cad_state_id']
        assert state in gallery.ids,(folder,state,'not in gallery')
        for key in ('cad_dwg','cad_dxf','cad_preview'):
            assert (base/row[key]).is_file(),(folder,row['row_id'],key)
        if state not in checked:
            cad=ezdxf.readfile(base/row['cad_dxf'])
            insert=next(e for e in cad.modelspace() if e.dxftype()=='INSERT')
            attrs={a.dxf.tag.upper():a.dxf.text.upper() for a in insert.attribs}
            image=Image.open(base/row['cad_preview']).convert('RGB')
            assert image.width>=300 and image.height>=300,(folder,state,'small preview')
            # Reject empty/near-blank images; inspect actual pixel diversity.
            colors=image.getcolors(image.width*image.height)
            assert colors and len(colors)>20,(folder,state,'blank preview')
            checked[state]=attrs
        if folder.startswith('SHIHLIN'): continue  # static BHL block has no pole attribute
        pole=row.get('pole_display')
        if pole:
            assert checked[state].get('POLES','').startswith(pole+'/'),(folder,row['row_id'],pole,checked[state])
        model=row['model'].upper()
        cad_type=checked[state].get('TYPE','')
        if folder.startswith('SCHNEIDER'):
            expected='IC60' if model=='IC60N' else 'IK60N' if model=='IK60N' else 'EZC250'
            assert cad_type==expected,(folder,row['row_id'],model,cad_type)
        elif model.startswith('AX'):
            assert model.startswith(cad_type+'-'),(folder,row['row_id'],model,cad_type)
        elif model in ('FH202','FH204'):
            assert cad_type==model,(folder,row['row_id'],model,cad_type)
        elif model.startswith('SH20'):
            assert cad_type=='SH200',(folder,row['row_id'],model,cad_type)
        elif model.startswith('S20'):
            assert cad_type=='S200',(folder,row['row_id'],model,cad_type)
        elif model.startswith(('XT1','XT2','XT3')):
            assert model.startswith(cad_type),(folder,row['row_id'],model,cad_type)
        elif model.startswith(('A1','A2','A3')):
            assert model.startswith(cad_type),(folder,row['row_id'],model,cad_type)
    summary[folder]={'rows':len(rows),'with_cad':sum(bool(r.get('cad_dwg')) for r in rows),
                     'distinct_cad_states':len(checked),'gallery_states':len(gallery.ids)}
print(json.dumps(summary,ensure_ascii=False))

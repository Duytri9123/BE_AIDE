"""Check that every published LS CAD view has working local files."""
import json
from html.parser import HTMLParser
from pathlib import Path

BASE=Path(__file__).resolve().parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/LS_D02_DU_LIEU_MOI'
class Reader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cards=[]
        self.options=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='article': self.cards.append(a.get('id'))
        if tag=='option': self.options.append(a)

reader=Reader()
reader.feed((BASE/'cad_views.html').read_text(encoding='utf8'))
broken=[]
for option in reader.options:
    for key in ('data-img','data-dwg','data-dxf'):
        if not option.get(key) or not (BASE/option[key]).exists():
            broken.append((option.get('value'),key))
prices=json.loads((BASE/'price_with_cad.json').read_text(encoding='utf8'))
for row in prices:
    for key in ('cad_preview','cad_dwg','cad_dxf'):
        if row.get(key) and not (BASE/row[key]).exists():
            broken.append((row['row_id'],key))
print(json.dumps({'devices':len(reader.cards),'view_choices':len(reader.options),
                  'price_rows':len(prices),'priced_with_cad':sum(bool(r['cad_dwg']) for r in prices),
                  'broken_links':broken},ensure_ascii=False))
if broken or len(reader.cards)!=33 or len(reader.options)!=165: raise SystemExit(1)

"""Check source-backed 2026 catalog pages, local links and prices."""
import json
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

base=Path(__file__).resolve().parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
folders=['LS_D02_DU_LIEU_MOI','MITSUBISHI_D04_DU_LIEU_MOI',
         'SCHNEIDER_D01_DU_LIEU_MOI','ABB_D03_DU_LIEU_MOI',
         'OSUNG_D05_DU_LIEU_MOI','SHIHLIN_D06_DU_LIEU_MOI']

class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links=[]
        self.script=[]
        self.inside_script=False
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in ('a','img'):
            self.links.append(attrs.get('href') or attrs.get('src'))
        if tag=='script':
            self.inside_script=True
    def handle_endtag(self,tag):
        if tag=='script':
            self.inside_script=False
    def handle_data(self,data):
        if self.inside_script:
            self.script.append(data)

summary={}
for folder in folders:
    page=base/folder/'index.html'
    doc=Tags();doc.feed(page.read_text(encoding='utf8'))
    assert doc.script,(folder,'no JS')
    with tempfile.TemporaryDirectory() as temp:
        js=Path(temp)/'catalog.js'
        js.write_text(''.join(doc.script),encoding='utf8')
        subprocess.run(['node','--check',str(js)],check=True,capture_output=True,text=True)
    broken=[]
    for link in doc.links:
        if not link or link.startswith('#') or urlsplit(link).scheme:
            continue
        target=(page.parent/unquote(urlsplit(link).path)).resolve()
        if not target.exists():
            broken.append(link)
    assert not broken,(folder,broken)
    data_file='price_grouped.json' if folder.startswith('MITSUBISHI') else (
        'price_with_cad.json' if folder.startswith('LS') else 'price_index.json')
    rows=json.loads((page.parent/data_file).read_text(encoding='utf8'))
    assert all(row.get('price_vnd',row.get('price_vnd_ex_vat',0))>0 for row in rows)
    summary[folder]={'rows':len(rows),'local_links':len(doc.links),'broken_links':len(broken)}

sch=json.loads((base/'SCHNEIDER_D01_DU_LIEU_MOI/price_index.json').read_text(encoding='utf8'))
assert len(sch)==117
assert next(x for x in sch if x['material_code']=='A9F74116')['price_vnd']==257400
assert next(x for x in sch if x['material_code']=='EZC250N3100')['price_vnd']==5072100
abb=json.loads((base/'ABB_D03_DU_LIEU_MOI/price_index.json').read_text(encoding='utf8'))
assert len(abb)==598
assert next(x for x in abb if x['material_code']=='1SDA066510R1')['price_vnd']==1468000
osu=json.loads((base/'OSUNG_D05_DU_LIEU_MOI/price_index.json').read_text(encoding='utf8'))
assert len(osu)==29
assert next(x for x in osu if x['material_code']=='OSS-612-PC-4P-A2-F')['price_vnd']==70150000
print(json.dumps(summary,ensure_ascii=False))

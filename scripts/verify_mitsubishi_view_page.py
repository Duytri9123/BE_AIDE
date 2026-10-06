"""Verify every displayed Mitsubishi CAD state resolves to its own files."""
import json
from html.parser import HTMLParser
from pathlib import Path

base=Path(__file__).resolve().parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/MITSUBISHI_D04_DU_LIEU_MOI'
native=base/'native'
manifest=json.loads((native/'manifest.json').read_text(encoding='utf8'))
views=json.loads((native/'views.json').read_text(encoding='utf8'))
prices=json.loads((base/'price_with_cad.json').read_text(encoding='utf8'))
grouped=json.loads((base/'price_grouped.json').read_text(encoding='utf8'))

class Reader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cards=[]
        self.options=[]
        self.selects=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='article': self.cards.append(a.get('id'))
        if tag=='select' and a.get('class')=='state': self.selects+=1
        if tag=='option': self.options.append(a)

reader=Reader()
reader.feed((base/'cad_gallery.html').read_text(encoding='utf8'))
def relevant(source, option):
    sid=source['id']
    if sid.startswith('MIT-D04-C2-'):
        own=source['dynamic_properties'][0]['value'].split(':')[0]
        return option==own+': Side View'
    if sid.startswith('MIT-D04-C3-'):
        own=source['dynamic_properties'][0]['value'].split(':')[0]
        return option in ('Side View',own+': Cover')
    return True

by_id={d['id']:d for d in manifest}
expected={d['id'] for d in manifest}|{v['id'] for v in views
         if relevant(by_id[v['source_id']],v['option'])}
shown={o.get('value') for o in reader.options}
broken=[]
for option in reader.options:
    for key in ('data-img','data-dwg','data-dxf'):
        if not option.get(key) or not (base/option[key]).exists():
            broken.append((option.get('value'),key))
for row in prices:
    for key in ('cad_preview','cad_dwg','cad_dxf'):
        if row.get(key) and not (base/row[key]).exists():
            broken.append((row['row_id'],key))
original_ids=[row['row_id'] for row in prices]
grouped_ids=[row_id for group in grouped for row_id in group['source_row_ids']]
group_issues=[]
if sorted(grouped_ids)!=sorted(original_ids):
    group_issues.append('Dòng PDF gốc bị thiếu hoặc lặp')
for group in grouped:
    if group['row_count']!=len(group['source_variants']):
        group_issues.append((group['display_id'],'variant_count'))
    if group['row_count']>1:
        members=[prices[row_id-1] for row_id in group['source_row_ids']]
        for key in ('model','pole_display','price_vnd','page','category','cad_state_id'):
            if len({str(row[key]) for row in members})!=1:
                group_issues.append((group['display_id'],key))
result={'devices':len(reader.cards),'selectors':reader.selects,
        'view_choices':len(reader.options),'price_rows':len(prices),
        'priced_with_cad':sum(bool(r['cad_dwg']) for r in prices),
        'display_rows':len(grouped),'group_issues':group_issues,
        'missing_states':sorted(expected-shown),'extra_states':sorted(shown-expected),
        'broken_links':broken}
print(json.dumps(result,ensure_ascii=False))
if (len(reader.cards)!=17 or reader.selects!=17 or len(reader.options)!=107 or
    result['missing_states'] or result['extra_states'] or broken or group_issues):
    raise SystemExit(1)

"""Recover explicit neutral-pole forms without equating them to protected 2P devices."""
import json,re
from pathlib import Path
from download_mitsubishi_priced_step import fetch,OUT,BASE,ROWS
from app.services.catalog_family_matching import row_poles

def main():
 discovered=json.loads((OUT/'discovered.json').read_text(encoding='utf8'));grouped={}
 for item in discovered:
  model=item['model'];name=item['file_name'].lower();poles=None;kind='MCB'
  if model in {'BH-D6','BH-D10'} and '4(3+n)' in name:poles='4P'
  elif model in {'BH-DN','BV-DN'}:
   poles='1P+N';kind='RCBO' if model=='BV-DN' else 'MCB'
  elif model=='BH-D6' and item['source_row'].startswith('2(1+N)P'):poles='1P+N'
  elif model=='BHW-T10' and item['source_row'].startswith('2(1+N)P'):poles='1P+N'
  if not poles:continue
  rows=[r for r in ROWS if row_poles(r)==poles and re.match(re.escape(model)+r'(?=$|\s)',r['item_name'],re.I)]
  if not rows:continue
  key=(item['source_url'],poles)
  if key not in grouped:grouped[key]={**item,'models':[],'price_row_ids':[],'poles':poles,'kind':kind}
  d=grouped[key];d['models']=sorted(set(d['models']+[model]));d['price_row_ids']=sorted(set(d['price_row_ids']+[r['id'] for r in rows]))
 done=[]
 originals={x['file_name']:x for x in json.loads((OUT/'downloads.json').read_text(encoding='utf8'))['downloaded']}
 for item in grouped.values():
  # Neutral 1P+N and fully protected 2P are separate logical catalog variants,
  # even where the manufacturer explicitly supplies the same geometric file.
  item['variant_suffix']='-1PN' if item['poles']=='1P+N' else ''
  done.append(fetch(item))
  folder=OUT/Path(item['file_name']).stem
  if item['variant_suffix']:
   (folder/'source-1pn.json').write_text(json.dumps(item,ensure_ascii=False,indent=2),encoding='utf8')
   if item['file_name'] in originals:(folder/'source.json').write_text(json.dumps(originals[item['file_name']],ensure_ascii=False,indent=2),encoding='utf8')
 (OUT/'mcb-remaining-downloads.json').write_text(json.dumps({'downloaded':done,'errors':[]},ensure_ascii=False,indent=2),encoding='utf8')
 print('Complete',len(done),'unique rows',len({r for x in done for r in x['price_row_ids']}),flush=True)
if __name__=='__main__':main()

"""Bind DR (drawout) price rows only to native drawout source bodies."""
import json
from pathlib import Path
from download_mitsubishi_priced_step import parse,fetch,OUT,BASE
def main():
 page=BASE+'/fa/download/cad/search.page?mode=cad&kisyu=%2Flvcb&category1=101'
 found=parse((OUT/'index-101.html').read_bytes(),page,'ACB');grouped={}
 for item in found:
  if '_dr' not in item['file_name'].lower() or not item['price_row_ids']:continue
  key=item['source_url']
  if key not in grouped:grouped[key]={**item,'models':[],'price_row_ids':[]}
  d=grouped[key];d['models']=sorted(set(d['models']+[item['model']]));d['price_row_ids']=sorted(set(d['price_row_ids']+item['price_row_ids']))
 done=[fetch(x) for x in grouped.values()]
 (OUT/'drawout-downloads.json').write_text(json.dumps({'downloaded':done,'errors':[]},ensure_ascii=False,indent=2),encoding='utf8')
 print('Complete',len(done),'rows',len({r for x in done for r in x['price_row_ids']}),flush=True)
if __name__=='__main__':main()

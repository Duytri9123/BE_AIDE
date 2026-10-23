"""Download only the named CP30-BA source body, keeping spring terminals distinct."""
import json,sys
from pathlib import Path
from download_mitsubishi_priced_step import parse,fetch,OUT,BASE,ROOT
def main():
 page=BASE+'/fa/download/cad/search.page?mode=cad&kisyu=%2Flvcb&category1=105'
 found=parse((ROOT/'tmp/mitsu-circuit-protectors.html').read_bytes(),page,'CB')
 done=[];held=[]
 for item in found:
  if not item['price_row_ids']:continue
  item['models']=[item['model']]
  if '_sq_' in item['file_name'].lower():
   held.append({**item,'reason':'Spring-clamp terminal body; supplier rows do not specify SQ option.'});continue
  done.append(fetch(item))
 (OUT/'protector-downloads.json').write_text(json.dumps({'downloaded':done,'held':held,'errors':[]},ensure_ascii=False,indent=2),encoding='utf8')
 print('Complete',len(done),'held',len(held),flush=True)
if __name__=='__main__':main()

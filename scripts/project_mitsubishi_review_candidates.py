"""Batch source projections; failures stay outside publication and do not stop discovery."""
import gc,json,sys
from pathlib import Path
from project_current_step_families import main as project_one
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'data/CatalogTB/Mitsubishi/NguonBenNgoai/PRIMARY-20261022'
def main():
 shard=int(sys.argv[1]);manifest=sys.argv[2] if len(sys.argv)>2 else 'downloads.json';items=json.loads((SRC/manifest).read_text(encoding='utf8'))['downloaded'];results=[]
 for index,item in enumerate(sorted(items,key=lambda x:x['file_name'])):
  if index%2!=shard:continue
  ident=Path(item['file_name']).stem
  try:
   sys.argv=['project','Mitsubishi','PRIMARY-20261022/'+ident];project_one();results.append({'family':ident,'status':'projected'})
  except Exception as e:results.append({'family':ident,'status':'held','error':str(e)});print('HELD',ident,str(e),flush=True)
  gc.collect()
 (SRC/(Path(manifest).stem+'-projection-results-'+str(shard)+'.json')).write_text(json.dumps(results,indent=2),encoding='utf8')
if __name__=='__main__':main()

import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB';OUT=ROOT/'docs/four-brands-additions-2026-10-22'
records=[]
for folder,ids,published in [
 ('ABB',['9AKK106930A4834','9AKK106930A4835','9AKK106930A4836','9AKK106930A4837','9AKK106930A4846','9AKK106930A4847','9AKK106930A4848','9AKK106930A4849'],{'9AKK106930A4834','9AKK106930A4835','9AKK106930A4836','9AKK106930A4837'}),
 ('LS',['55466','55467','55468','55469','55470','55471'],{'55466','55467','55468','55469','55470','55471'}),
 ('Chint',['KG316T','NKG1']+['NXB-63-'+p for p in ['1P','2P','3P','4P']]+['NB1-63H-'+p for p in ['1P','2P','4P']]+['NDK-'+str(n) for n in [25,50,100,150,200,250,300,400,500,700,1000,1500,2000,2500,3000,4000,5000]],{'KG316T','NKG1'})]:
 for ident in ids:
  p=CAT/folder/'NguonBenNgoai'/ident;source=json.loads((p/'source.json').read_text(encoding='utf8'));review=json.loads((p/'review.json').read_text(encoding='utf8')) if (p/'review.json').exists() else None
  records.append({'brand_folder':folder,'source_id':ident,'source_url':source.get('source_url') or source.get('url'),'source_page':source.get('source_page'),'sha256':source.get('sha256'),'status':'six_views_published' if ident in published else 'held_not_published' if review else 'original_2d_retained_for_reference','review':review})
records.append({'brand_folder':'Schneider','source_id':'LRD14 / MCADPD0004675','source_page':'https://nuovaelva.it/store/en/shop/brands/TEL/items/LRD14','status':'existing_six_view_geometry_reused','download_comparison':'lrd14-file-hashes.json','electrical_reference':'https://www.se.com/uk/en/product/LRD14/'})
(OUT/'source-search.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
print('Recorded',len(records),'source records;',sum(r['status']=='held_not_published' for r in records),'held source sets')

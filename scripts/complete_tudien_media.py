from build_tudien_library import *
def load(p):return json.loads(p.read_text(encoding='utf8'))
media=load(OUT/'embedded_media.json');candidates=[]
for m in media:
 p=OUT/'nguon/embedded_media'/f"{m['id']}_ocr.json"
 if p.exists():
  o=load(p);m['ocr_file']=str(p.relative_to(OUT)).replace('\\','/');m['ocr_lines']=len(o['lines']);m['status']='machine_read_and_visual_overview_reviewed'
  for line in o['lines']:
   t=line['text']
   if re.search(r'[A-Za-z]{2,}[-]?[0-9]+[A-Za-z0-9+/-]*',t):candidates.append({'media_id':m['id'],'text':t,'confidence':line['confidence'],'polygon':line['polygon'],'status':'OCR_candidate_not_verified_SKU','sources':m['sources']})
save(OUT/'embedded_media.json',media);save(OUT/'ocr_model_candidates.json',candidates)
queue=load(OUT/'review_queue.json');queue['embedded_images']=[{'id':m['id'],'path':m['path'],'ocr_file':m.get('ocr_file'),'reason':'Machine-read full image; exact order-code characters and handwritten quantities require source confirmation before SKU/CAD matching.'} for m in media if not m.get('observed_text','').startswith('Logo')]
save(OUT/'review_queue.json',queue);print('OCR images',sum('ocr_file' in m for m in media),'model text candidates',len(candidates))

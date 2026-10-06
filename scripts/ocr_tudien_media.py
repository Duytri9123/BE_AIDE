import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT.parent/'tmp/tudien_ocr'))
from rapidocr_onnxruntime import RapidOCR
OUT=ROOT/'data/tudien';engine=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=1)
media=json.loads((OUT/'embedded_media.json').read_text(encoding='utf8'))
for m in media:
 target=OUT/'nguon/embedded_media'/f"{m['id']}_ocr.json"
 if target.exists():continue
 try:
  result,_=engine(str(OUT/m['path']));lines=[{'polygon':r[0],'text':r[1],'confidence':r[2]} for r in result or []]
  target.write_text(json.dumps({'source_media_id':m['id'],'method':'local_RapidOCR','status':'machine_read_not_manually_certified','lines':lines},ensure_ascii=False,indent=2),encoding='utf8')
  print(m['id'],len(lines),flush=True)
 except Exception as e:print(m['id'],str(e),flush=True)

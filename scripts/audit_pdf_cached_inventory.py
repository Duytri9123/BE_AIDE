"""Read-only category diagnostics for a supplied PDF's cached page responses."""
import io, hashlib, json, sys
from pathlib import Path
from collections import Counter
import pypdfium2 as pdfium
import redis
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.core.config import settings
from app.services.ai.response_parser import ResponseParserService

doc=pdfium.PdfDocument(sys.argv[1])
image=doc[0].render(scale=3).to_pil().convert('RGB')
if max(image.size)>4096:
    from PIL import Image
    factor=4096/max(image.size)
    image=image.resize(tuple(int(v*factor) for v in image.size),Image.Resampling.LANCZOS)
data=io.BytesIO();image.save(data,format='JPEG',quality=85,optimize=True)
digest=hashlib.sha256(data.getvalue()).hexdigest()
client=redis.Redis.from_url(settings.REDIS_URL,decode_responses=True,socket_timeout=10)
rows=[]
for key in client.scan_iter(match=f'ai_vision:{digest}:*',count=100):
    value=client.get(key)
    try: value=json.loads(value)
    except (TypeError,ValueError): pass
    if not isinstance(value,str): continue
    devices=ResponseParserService.parse_device_list(value)
    if devices:
        counts=Counter()
        for d in devices: counts[(d.panel_code,d.category)]+=d.quantity
        rows.append({'cache_variant':key.split(':')[-2], 'counts':[[*k,v] for k,v in counts.items()]})
print(json.dumps(rows,ensure_ascii=True))

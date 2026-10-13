"""Read only the two device silhouettes from the official vector PDF."""
from pathlib import Path
import ctypes,json
import pypdfium2 as pdfium
import pypdfium2.raw as raw

root=Path(__file__).resolve().parents[2]
doc=pdfium.PdfDocument(str(root/'outputs/sample-cad-recovery/NCH8-2P-official.pdf'))
regions={'front':(290,129,497,176),'side':(290,262,497,424)}
result={}
for name,region in regions.items():
    paths=[]
    for obj in doc[0].get_objects():
        x0,y0,x1,y1=obj.get_bounds()
        if obj.type!=raw.FPDF_PAGEOBJ_PATH or not (region[0]<=x0<=x1<=region[2] and region[1]<=y0<=y1<=region[3]):continue
        matrix=obj.get_matrix();segments=[]
        for i in range(raw.FPDFPath_CountSegments(obj.raw)):
            segment=raw.FPDFPath_GetPathSegment(obj.raw,i)
            x,y=ctypes.c_float(),ctypes.c_float()
            if not raw.FPDFPathSegment_GetPoint(segment,ctypes.byref(x),ctypes.byref(y)):raise ValueError('Invalid PDF point')
            px,py=matrix.on_point(x.value,y.value)
            segments.append({'type':raw.FPDFPathSegment_GetType(segment),'point':[px,py],
                             'close':bool(raw.FPDFPathSegment_GetClose(segment))})
        paths.append(segments)
    if not paths:raise ValueError('No source paths for '+name)
    result[name]=paths
(root/'outputs/sample-cad-recovery/NCH8-official-paths.json').write_text(json.dumps(result),encoding='utf8')
print({k:len(v) for k,v in result.items()})

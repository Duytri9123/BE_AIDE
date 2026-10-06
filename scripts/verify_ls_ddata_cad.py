"""Check D:\\data CAD imports and the LS price links they support."""
import json
from pathlib import Path
from PIL import Image, ImageChops
import ezdxf

base=Path(__file__).resolve().parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/LS_D02_DU_LIEU_MOI'
native=base/'native'
rows=json.loads((base/'price_with_cad.json').read_text(encoding='utf8'))
by_id={r['row_id']:r for r in rows}
expected={
    29:('LS-DATA-TS1250A3P',3),
    30:('LS-DATA-TS1600AF-3P',3),
    32:('LS-DATA-TS1250A3P',3),
    33:('LS-DATA-TS1600AF-3P',3),
    50:('LS-D02-C5-I07',4),
    51:('LS-DATA-TS1600AF-4P',4),
    53:('LS-D02-C5-I07',4),
    54:('LS-DATA-TS1600AF-4P',4),
    161:('LS-DATA-MC32AF-3P',3),
    170:('LS-DATA-MC185-225-3P',3),
    171:('LS-DATA-MC185-225-3P',3),
    172:('LS-DATA-MC265-400-3P',3),
    173:('LS-DATA-MC265-400-3P',3),
    174:('LS-DATA-MC265-400-3P',3),
    175:('LS-DATA-MC500-800-3P',3),
    176:('LS-DATA-MC500-800-3P',3),
    177:('LS-DATA-MC500-800-3P',3),
}
for row_id,(stem,poles) in expected.items():
    row=by_id[row_id]
    assert row['poles_pdf']==poles,(row_id,'poles')
    assert row['cad_device_id']==stem,(row_id,'CAD')
    assert row['cad_match_level']=='family',(row_id,'match level')
    for ext in ('.dwg','.dxf','-verified.png','-source.json'):
        assert (native/(stem+ext)).is_file(),(stem,ext)
    cad=ezdxf.readfile(native/(stem+'.dxf'))
    assert sum(1 for _ in cad.modelspace())>0,(stem,'empty CAD')
    image=Image.open(native/(stem+'-verified.png')).convert('RGB')
    assert image.getextrema()!=((0,0),(0,0),(0,0)),stem
same=ImageChops.difference(
    Image.open(native/'LS-DATA-TS1250A3P-verified.png').convert('RGB'),
    Image.open(native/'LS-D02-C5-I06-verified.png').convert('RGB'))
assert same.getbbox() is None,'TS1250A3P and D02 TS1000 3P frame preview differ'
for row_id in (82,90):
    assert by_id[row_id]['poles_pdf']==1,(row_id,'1P')
    assert by_id[row_id]['cad_dwg'] is None,(row_id,'unverified LA63 CAD')
print(json.dumps({'new_price_links':len(expected),'LS_rows_with_cad':sum(bool(r['cad_dwg']) for r in rows),
                  'LA63_1P_recognized':True,'TS1250_frame_pixels_identical':True}))

"""Extract exact text evidence from the supplied DWF ePlot, without claiming CAD matches.

DWF V06 stores a zipped W2D plot. Its text labels are useful evidence, but it
does not expose the DWG block identities or dynamic visibility states needed
to make a verified per-device DWG/DXF association.
"""
import hashlib
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / 'Tudien/CATALOG_PHU_KIEN_DOC_LAP/LS_D02_DU_LIEU_MOI'
SOURCE = Path(sys.argv[1]) if len(sys.argv)>1 else Path(r'E:\Downloads\@LS_recover.dwf')
DEST = BASE / 'source' / SOURCE.name
DEST.parent.mkdir(exist_ok=True)
if SOURCE.resolve() != DEST.resolve():
    shutil.copy2(SOURCE, DEST)
raw = DEST.read_bytes()
assert raw.startswith(b'(DWF V06.00)PK\x03\x04'), 'Unexpected DWF container'
with zipfile.ZipFile(DEST) as archive:
    plot = archive.read(next(name for name in archive.namelist() if name.lower().endswith('.w2d')))
    metadata = archive.read('manifest.xml').decode('utf8', 'replace')
    assert 'AutoCAD' in metadata

# ASCII text operators in this ePlot are quoted. Ignore binary and font strings.
labels = sorted({s.decode('latin1', 'replace').strip()
                 for s in re.findall(rb"'((?:[^'\\]|\\.){2,150})'", plot)
                 if len(s)<100 and re.search(rb'[A-Za-z0-9]', s)})
rows = json.loads((BASE/'price_with_cad.json').read_text(encoding='utf8'))
matches = []
for row in rows:
    model = row['model']
    if row.get('cad_dwg') or len(model)<4 or not re.search(r'\d', model):
        continue
    exact_text = [label for label in labels if re.search(
        r'(?<![A-Z0-9])'+re.escape(model.upper())+r'(?![A-Z0-9])', label.upper())]
    if exact_text:
        matches.append({'row_id':row['row_id'], 'model':model,
                        'dwf_text_labels':exact_text[:8],
                        'status':'Model appears in DWF plot text; device geometry not identified'})

result = {'source_original':str(SOURCE), 'source_copy':'source/'+DEST.name,
          'sha256':hashlib.sha256(raw).hexdigest(), 'format':'DWF V06 ePlot / W2D',
          'source_autocad':'AutoCAD 2022' if '2022' in metadata else 'AutoCAD',
          'plot_bytes':len(plot), 'unique_plot_text_labels':len(labels),
          'unmatched_price_rows_with_model_text':len(matches),
          'interpretation':'DWF text is evidence that a model label occurs in the plot; it does not identify an original DWG block, pole count, or CAD geometry for that price row.',
          'matches':matches}
(BASE/'recover_dwf_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'source_sha256':result['sha256'],'text_labels':len(labels),
                  'unmatched_price_rows_with_model_text':len(matches)},ensure_ascii=False))

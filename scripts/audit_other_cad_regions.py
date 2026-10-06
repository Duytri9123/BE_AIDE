"""Find device blocks elsewhere in the original CAD catalog."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / 'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
TERMS = ('LA63N', 'LA63H', 'S-T12', 'S-T20', 'OSUNG', 'O-SUNG',
         'SHIHLIN', 'SCHNEIDER', 'ABB', 'MITSUBISHI', 'BHL', 'IC60',
         'XT1', 'S200', 'EZC', 'NSX', 'LC1D', 'BH-D6')
for path in ROOT.rglob('thong_tin.json'):
    data = json.loads(path.read_text(encoding='utf-8'))
    label = ' '.join(str(data.get(k) or '') for k in
                     ('source_block_name', 'display_name', 'text_evidence',
                      'specification_candidates', 'brand_mentions')).upper()
    matches = [term for term in TERMS if term in label]
    if matches:
        print(path.relative_to(ROOT), '|', ','.join(matches), '|',
              data.get('classification'), '|', data.get('cad', {}).get('status'),
              '|', data.get('zones'), '|', str(data.get('source_block_name'))[:60])

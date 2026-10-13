"""Record reviewed manufacturer dimensions without relabelling BKN CAD."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[2]
out = root / 'outputs/sample-cad-recovery'
source = out / 'LS-official-202409.pdf'
report = {
    'source_url': 'https://www.ls-electric.com/ko/cat/%5BDevice%5D_Electric_Product_EN_C19912-65-202409.pdf',
    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'page': 4,
    'models': {
        'LA63N': {'breaking_capacity_ka': 6},
        'LA63H': {'breaking_capacity_ka': 10},
    },
    'reviewed_1p_dimension_labels_mm': {
        'width': 17.6, 'body_height': 83, 'depth_dimension': 72,
        'body_depth': 65, 'din_reference_height': 35.5,
    },
    'limitations': [
        'Dimension labels are distinct from the full visible envelope and terminal clearance.',
        'The DIN clip and handle protrusions require separate projection inspection.',
        'This page does not establish complete 2P/3P CAD geometry.',
        'BKN source CAD is not an exact LA63 model drawing.',
    ],
    'exact_cad_binding_verified': False,
    'fabrication_ready': False,
}
(out / 'LA63-official-evidence.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
print('Saved reviewed LA63 dimension evidence; no inferred CAD model binding.')

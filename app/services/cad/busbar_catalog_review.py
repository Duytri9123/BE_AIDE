"""Catalog proposals preserve geometry and never treat density estimates as rated ampacity."""
import json
from pathlib import Path
PATH=Path(__file__).resolve().parents[3]/'data/catalog_accessories.json'
def review(current,required_length_mm=None):
 rows=json.loads(PATH.read_text(encoding='utf8'))['busbar']['items']
 usable=[b for b in rows if b.get('phase')=='L1' and float(b.get('I_estimated') or b.get('I_rated') or 0)>=float(current or 0)]
 selected=min(usable,key=lambda b:(b['section_mm2'],b['thickness_mm'])) if current and usable else None
 return dict(status='proposal_requires_verification' if selected else 'needs_current_or_catalog',selected=selected,required_length_mm=required_length_mm,stock_length_is_route_length=False,neutral_section_policy='do_not_reduce_without_load_and_harmonic_review',release_ready=False,required=['temperature_rise','ambient','short_circuit','supports','terminal_joint','clearance','neutral_harmonics'])

"""Audit all currently published CHINT price rows against usable public CAD."""
import collections
import json
import sys
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.services.library_catalog_information import source_rows
from app.services.price_row_cad_detail import linked_cad_for_row


def pending_reason(row):
 model=row['sku']
 if model.startswith('AX-3'):
  return 'Reviewed CHINT Korea native AX accessory CAD exists, but no usable current public link was found; check profile publication and configuration digests.'
 if model in {'MI-5','MI-6','MI-7'}:
  return 'Reviewed CHINT Kazakhstan native MI accessory reference exists, but no usable current public link was found; check profile publication and configuration digests.'
 if model=='AC30-124':
  return 'Reviewed CHINT AC30 engineering sheet has other three-pin variants, but AC30-124 is a universal three-pin socket with a different aperture/body variant. No manufacturer drawing currently corroborates its envelope; do not copy the pictured non-universal aperture.'
 if model=='NXB-125':return 'Manufacturer offers Parasolid x_t sources; no reviewed DXF view available yet.'
 if model=='NXM-1250H':return 'No reviewed 1250-frame projection available; do not substitute a different frame.'
 if model.startswith('NXR-25'):return 'No source for this frame; NXR-12/38 have different body dimensions.'
 if model.startswith('NXR-200'):return 'Native terminal/assembly configuration still unresolved against the manufacturer mounting drawing.'
 if model=='NXR-630':return 'Higher-current terminal pitch differs from the available 125–400A CAD.'
 if model.startswith('NDK-'):return 'Native source retained; per-model mounting orientation and winding variant remain unreviewed.'
 if model.startswith('NP2'):return 'Operator-head/contact variant not yet resolved to a reviewed drawing.'
 if model=='KG316T':return 'Existing 220V timer source does not resolve all electrical/assembly variants in the price row.'
 return 'No reviewed CAD source for this published model/configuration in the current library.'


def main():
 snapshot=json.loads((ROOT/'data/CatalogTB/_agent_index/browser_display_v5.json').read_text(encoding='utf8'))
 devices=[d for d in snapshot['items'] if d.get('brand')=='CHINT']
 report=[]
 for row in source_rows():
  if row.get('brand')!='CHINT':continue
  linked=linked_cad_for_row(row,devices)
  report.append({'price_row_id':row['id'],'model':row['sku'],'category':row['category'],
   'specifications':row.get('specifications') or {},'status':'available' if linked else 'pending',
   'cad_devices':[{'id':d['id'],'views':len(d['views']),'scope':d['link_scope']} for d in linked],
   **({'geometry_reference_scope':'conservative_family_planning_envelope_only','reference_limit':'AC30-124 has a 36×80 mm space-reservation outline inferred from the documented three-pin AC30 family. This is not manufacturer-confirmed exact AC30-124 geometry.'} if linked and row['sku']=='AC30-124' else {}),
   **({} if linked else {'reason':pending_reason(row)})})
 counts={'available':0,'pending':0,**dict(collections.Counter(r['status'] for r in report))}
 payload={'checked_on':datetime.now(timezone.utc).date().isoformat(),'scope':'All current published CHINT source rows',
  'policy':'GPT visual/model-family geometry review; nameplate suffix differences alone do not exclude CAD. Electrical ratings remain those of the price row.',
  'coverage_note':'Available includes partial orthographic catalogue references and explicitly labelled dimension-based mounting/envelope outlines; it does not imply a full manufacturer CAD model or automatic insertion approval.',
  'conservative_family_planning_envelope_rows':[r['price_row_id'] for r in report if r.get('geometry_reference_scope')=='conservative_family_planning_envelope_only'],
  'total_rows':len(report),'counts':counts,'items':report}
 (ROOT/'app/data/chint_cad_coverage_review.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'total_rows':len(report),**counts}),flush=True)


if __name__=='__main__':main()

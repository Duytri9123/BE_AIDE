"""Publish unresolved model bindings as evidence, not fictitious catalog devices."""
import json
from pathlib import Path
from app.services.cad.automatic_selection import select_device_geometry
from app.services.cad.catalogtb_assets import ROOT
from app.services.ai.quotation_configuration import apply_configuration

folder=ROOT.parents[2]/'outputs/workspace-457-e2e'
report=json.loads((folder/'approved-quotation-configuration.json').read_text(encoding='utf8'))
rows=apply_configuration(report['devices'],report['configuration'])
groups={}
for row in rows:
    key=(row['category'],row.get('brand'),row.get('part_number'),row.get('poles'),row.get('in_a'),row.get('icu_ka'))
    if key not in groups:
        selected=select_device_geometry(row)
        groups[key]={'category':key[0],'brand':key[1],'requested_model':key[2],'poles':key[3],
                     'current_a':key[4],'breaking_capacity_ka':key[5], 'quantity':0,
                     'automatic_selection':(selected.get('cad') or {}).get('automatic_selection'),
                     'source_evidence':[], 'status':'matched_reference_geometry' if (selected.get('cad') or {}).get('asset_id') else 'needs_source_model_binding'}
    groups[key]['quantity']+=row['quantity']
    evidence=(row.get('source_observations') or {}).get('quotation',{}).get('evidence')
    if evidence not in groups[key]['source_evidence']: groups[key]['source_evidence'].append(evidence)
raw=json.loads((folder/'raw-control-spatial-audit.json').read_text(encoding='utf8'))
result={'purpose':'Các yêu cầu cấu hình chưa ghép đủ model/mặt CAD; không phải danh mục thiết bị mới.',
        'source_cad_sha256':raw['source_sha256'],'blocks_scanned':raw['blocks_scanned'],
        'source_unchanged':raw['source_unchanged'],'physical_quantity':sum(r['quantity'] for r in groups.values()),
        'requests':list(groups.values()),'literal_model_labels':sorted({h['text'] for h in raw['text_hits'] if any(m in h['text'].upper() for m in ('NCH8','LA63','KG316'))}),
        'policy':'Không báo không có thư viện, không thay model/hãng, không đặt tên lại hình giống nhau để bỏ qua xác minh.'}
(ROOT/'thiet_bi_can_ghep_model.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
(folder/'approved-model-bindings.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'groups':len(groups),'physical_quantity':result['physical_quantity'],
                  'pending_groups':sum(r['status']=='needs_source_model_binding' for r in groups.values())}))

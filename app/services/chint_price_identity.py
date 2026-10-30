"""Resolve NXR from the model column of one reviewed supplier PDF, not fitment."""
import copy,json,re
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=1)
def identity_registry():
 return json.loads((Path(__file__).resolve().parents[1]/'data/chint_nxr_material_codes.json').read_text(encoding='utf8'))

def normalize_nxr_row(row,registry=None):
 if str(row.get('brand') or '').upper()!='CHINT':return row
 registry=identity_registry() if registry is None else registry
 if row.get('source_sha256')!=registry['source_sha256'] or row.get('source_page')!=registry['pdf_page']:return row
 spec=row.get('specifications') or {};code=str(spec.get('Mã hàng') or spec.get('Mã đặt hàng') or '').strip();entry=registry['items'].get(code)
 if not entry:return row
 expected=entry['setting_current_a'];observed=spec.get('Dải chỉnh định Ir (A)') or spec.get('In')
 numbers=lambda value:re.findall(r'\d+(?:\.\d+)?',str(value).replace(',','.'))
 if observed and [float(n) for n in numbers(observed)]!=[float(n) for n in numbers(expected)]:
  raise ValueError(f'CHINT material {code}: setting range disagrees with reviewed source PDF')
 if row.get('sku')==entry['model'] and row.get('category')=='THERMAL_RELAY' and spec.get('Dải chỉnh định Ir (A)')==expected and 'In' not in spec and (not registry.get('phase_evidence') or spec.get('Số cực')=='3P'):return row
 out=copy.deepcopy(row)
 if 'source_extraction_original' not in out:
  out['source_extraction_original']={k:copy.deepcopy(row.get(k)) for k in ('sku','name','item_name','category','group','specifications','columns','cells')}
 out.update(sku=entry['model'],name=entry['model'],item_name=entry['model'],category='THERMAL_RELAY',group='NXR · THERMAL_RELAY')
 updated=dict(spec);updated.pop('In',None);updated.update({'Họ thiết bị':entry['family'],'Dải chỉnh định Ir (A)':expected});out['specifications']=updated
 if registry.get('phase_evidence'):
  updated['Số cực']='3P'
  out['phase_configuration_review']=registry['phase_evidence']
 if out.get('cells'):out['cells'][0]=entry['model']
 if out.get('columns'):out['columns']=['Dải chỉnh định Ir (A)' if k=='In' else k for k in out['columns']]
 out['source_identity_review']={'source_material_code':code,'identity_source_url':registry['source_url'],'identity_source_sha256':registry['source_sha256'],'identity_source_page':registry['pdf_page'],'reviewed_on':registry['checked_at'],'reason':'Explicit NXR model column in the original supplier PDF identifies the thermal relay and setting range. Compatible NXC contactor is a separate fitment field. Manufacturer NXR catalog corroborates the product family; regional material codes are not treated as global aliases.'}
 return out


def normalize_nm8n125_row(row,registry=None):
 """Qualify reviewed AC ratings; never extrapolate them to DC or other frames."""
 registry=identity_registry() if registry is None else registry
 proof=registry.get('nm8n125_rating_evidence')
 if not proof or str(row.get('brand') or '').upper()!='CHINT':return row
 if row.get('source_sha256')!=registry['source_sha256'] or row.get('source_page') not in (39,40,41,42):return row
 match=re.fullmatch(r'NM8N-125([CSH]) TM (16|20|25|32|40|50|63|80|100|125) (1P|2P|3P|4C)',str(row.get('sku') or ''))
 if not match:return row
 capacity,current,poles=match.groups();spec=row.get('specifications') or {};expected={'C':'36kA','S':'50kA','H':'100kA'}[capacity]
 if poles=='1P' and capacity!='C':raise ValueError('Unreviewed NM8N-125 single-pole variant')
 if spec.get('Icu')!=expected or spec.get('Ics')!='100%' or spec.get('Số cực')!=('4P' if poles=='4C' else poles):raise ValueError('NM8N-125 pricebook ratings disagree with reviewed manufacturer table')
 voltage='220/230/240 V AC' if poles=='1P' else '380/400/415 V AC'
 if spec.get('Điện áp công bố Icu/Ics')==voltage and row.get('electrical_rating_review')==proof and (not row.get('columns') or 'Điện áp công bố Icu/Ics' in row['columns']):return row
 out=copy.deepcopy(row);out['specifications']['Điện áp công bố Icu/Ics']=voltage;out['electrical_rating_review']=proof
 if out.get('columns') and 'Điện áp công bố Icu/Ics' not in out['columns']:
  out['cells']=list(out.get('cells') or [])
  out['cells']+=['']*max(0,len(out['columns'])-len(out['cells']))
  out['columns'].append('Điện áp công bố Icu/Ics');out['cells'].append(voltage)
 return out

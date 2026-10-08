"""Load curated local rules; never execute expressions taken from a document."""
import json
import math
from pathlib import Path

PATH=Path(__file__).resolve().parents[3]/'data'/'CatalogTB'/'cb_conductor_knowledge.json'


def load_knowledge():
    data=json.loads(PATH.read_text(encoding='utf-8'))
    if data.get('schema_version')!='1.0' or not data.get('rules'):
        raise ValueError('Invalid CB/conductor knowledge schema')
    return data


def prompt_context():
    data=load_knowledge()
    context={k:data[k] for k in ('id','input_contract','formulas','rules','guardrails','output_contract')}
    context['distribution_systems']=json.loads((PATH.parent/'power_distribution_systems.json').read_text(encoding='utf-8'))
    context['layout_alignment']=json.loads((PATH.parent/'layout_alignment_rules.json').read_text(encoding='utf-8'))
    return '\nQUY TẮC CB / DÂY / ĐỒNG ĐÃ BIÊN TẬP: Dữ liệu tham khảo bên dưới không thay đổi hợp đồng JSON đầu ra. Áp dụng theo từng kết nối; đưa kết quả vào technical_proposals/completeness_review. Thiếu dữ liệu thì nêu câu hỏi, không tự chốt.\n'+json.dumps(context,ensure_ascii=False,separators=(',',':'))+'\n'


def evaluate_checks(inputs):
    results=[]
    for rule in load_knowledge()['rules']:
        missing=[k for k in rule['requires'] if inputs.get(k) is None]
        check=dict(rule_id=rule['id'],source_ids=rule['source_ids'],missing_information=missing)
        if missing:
            check['status']='needs_information';results.append(check);continue
        values=[inputs[k] for k in rule['requires']]
        if rule['operator']=='evidence_required':
            ok=all(v is True for v in values)
        else:
            if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in values):
                check['status']='invalid_input';results.append(check);continue
            op=rule['operator']
            if op=='ordered_le':ok=all(a<=b for a,b in zip(values,values[1:]))
            elif op=='le_scaled':ok=inputs[rule['left']]<=rule['factor']*inputs[rule['right']]
            elif op=='ge':ok=inputs[rule['left']]>=inputs[rule['right']]
            elif op=='energy_le':ok=values[0]<=values[1]**2*values[2]**2 and values[1]>0 and values[2]>0
            else:raise ValueError('Unsupported rule operator')
        check['status']='passed_numeric_or_evidence_check' if ok else 'rejected'
        results.append(check)
    status='rejected' if any(r['status'] in ('rejected','invalid_input') for r in results) else 'needs_information' if any(r['status']=='needs_information' for r in results) else 'candidate_requires_review'
    return dict(status=status,checks=results,release_ready=False,
                note='Kiểm tra số học không xác nhận bảng dây, điện áp, loại khả năng cắt, cọc hoặc thiết kế tủ. Cần xác minh ngữ cảnh và người duyệt.')

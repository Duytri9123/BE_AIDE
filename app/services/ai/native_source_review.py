"""Resolve a disputed field from its uniquely bound CAD label, never proximity."""
import re

from app.services.ingestion.cad_source_evidence import plain, signature


def adjudicate_native_fields(evidence, parts, issues, native_path=None):
    from app.services.ai.source_issue_review import is_inventory_duplicate_issue
    labels={r['id']:r for r in evidence.get('labels',[])}
    remaining,proofs=[],[]
    control_labels={}
    for issue in issues:
        region=str(issue.get('region_id','')) if isinstance(issue,dict) else ''
        field=issue.get('field') if isinstance(issue,dict) else None
        indices=issue.get('device_indices') if isinstance(issue,dict) else None
        # Inventory/quantity/duplicate disputes require a separate source scan.
        if (not region.isdigit() or int(region)>=len(parts) or field not in {'tag','spec','connected_load','category'}
                or not isinstance(indices,list) or not indices
                or is_inventory_duplicate_issue(issue)
                or re.search(r'thiếu.*(?:thiết bị|dòng)|missing.*(?:device|row)',str(issue.get('reason') or ''),re.I)):
            remaining.append(issue);continue
        checks=[]
        reason = plain(issue.get('reason') or '')
        missing_control_label = (native_path and field in {'spec', 'category'}
                                 and re.search(r'KHONG (?:CO (?:CHU|NHAN)|GHI)', reason))
        if missing_control_label and region not in control_labels:
            from app.services.ai.cad_branch_evidence import seed_control_label_boxes
            control_labels[region] = {int(box['device_id']): box for box in seed_control_label_boxes(
                native_path, None, parts[int(region)]['devices'], [], evidence=evidence)
                if box.get('cad_control_label_id') and box.get('load_box_2d')}
        for index in indices:
            rows=parts[int(region)]['devices']
            if type(index) is not int or not 0<=index<len(rows):break
            row=rows[index];ids=set(row.get('source_evidence_ids') or [])
            control = control_labels.get(region, {}).get(index) if missing_control_label else None
            if (control and plain(control['cad_control_label_text']) in reason
                    and plain(row.get('spec') or '').strip() in {'', plain(control['cad_control_label_text']).strip()}
                    and all(row.get(rating) is None for rating in ('poles', 'in_a', 'icu_ka'))):
                checks.append((row, {'field':field, 'value':row.get(field), 'observed_text':control['cad_control_label_text'],
                                    'source_evidence_ids':[control['cad_control_label_id']], 'verification_status':'native_label',
                                    'method':'distinct_cad_control_rectangle'}))
                continue
            if field=='category':break
            matches=[r for r in evidence.get('rows',[]) if {r['id'],r['rating_id']}.issubset(ids)]
            if len(matches)!=1:break
            source=matches[0];value=row.get(field)
            label=labels.get(source['id' if field=='tag' else 'rating_id'])
            if field=='connected_load':
                circuit=(row.get('source_observations') or {}).get('circuit') or {}
                bound=[labels[i] for i in circuit.get('evidence_ids',[]) if i in labels
                       and value and plain(labels[i]['text']).strip()==plain(value).strip()]
                if circuit.get('source')!='cad_row' or len(bound)!=1:break
                label=bound[0]
            if not label or not value:break
            expected=source.get('tag') if field=='tag' else source.get('rating')
            if field=='tag' and plain(value).strip()!=plain(expected).strip():break
            if field=='spec' and signature(value)!=signature(expected):break
            checks.append((row,{'field':field,'value':value,'observed_text':label['text'],
                               'source_evidence_ids':[label['id']], 'verification_status':'native_label',
                               'method':'exact_bound_cad_row'}))
        control_ids = [check['source_evidence_ids'][0] for _, check in checks
                       if check['method'] == 'distinct_cad_control_rectangle']
        if len(checks)!=len(indices) or len(control_ids) != len(set(control_ids)):
            remaining.append(issue);continue
        for row,check in checks:
            observed=row.get('source_observations') or {}
            row['source_observations']={**observed,'source_checks':[*(observed.get('source_checks') or []),check]}
        proofs.append({'record_kind':'note','region_id':region,'verification_status':'native_label',
                       'observed_text':' / '.join(c['observed_text'] for _,c in checks),
                       'confirmed_values':[c for _,c in checks]})
    return remaining,proofs

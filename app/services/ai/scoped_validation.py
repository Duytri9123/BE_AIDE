"""Reuse completed coverage/crop checks within one server-owned EL operation."""
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

CLAIM_FIELDS = ('name','category','tag','spec','quantity','unit','panel_code','source_file_id','source_page',
                'poles','in_a','icu_ka','connected_load','quantity_basis','drawing_quantity','source_observations','evidence_region')


def claim_key(row):
    return hashlib.sha256(json.dumps({k:row.get(k) for k in CLAIM_FIELDS},sort_keys=True,
                         ensure_ascii=False,default=str).encode()).hexdigest()


def source_revision(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@dataclass(frozen=True)
class ScopedValidation:
    # This Python object is constructed only by the extraction branch. A JSON
    # context sent by a client cannot instantiate a trusted validation object.
    claims: tuple
    revisions: tuple

    def matches(self, files, rows, observations):
        selected={f.id:f for f in files}
        if not rows or any(r.get('source_file_id') not in selected for r in rows):
            return False
        for row in rows:
            if not any(isinstance(o,dict) and o.get('tool') == 'read_project_sources'
                and row['source_file_id'] in (o.get('arguments') or {}).get('file_ids', [])
                and (o.get('arguments') or {}).get('source_page') == row.get('source_page')
                and (o.get('arguments') or {}).get('source_region') == (row.get('evidence_region') or {}).get('source_region')
                for o in observations):
                return False
        relevant={r['source_file_id'] for r in rows}
        for file_id,path,revision in self.revisions:
            if file_id in relevant:
                file=selected.get(file_id)
                if file is None or str(Path(file.file_path).resolve()) != path or source_revision(path) != revision:
                    return False
        actual=Counter(claim_key(r) for r in rows)
        # A per-panel verifier receives only that panel's subset. Its complete
        # claim multiset must match the corresponding scope, including counts.
        scopes={(r['source_file_id'],r.get('source_page'),r.get('panel_code')) for r in rows}
        needed=Counter()
        for scope,claims in self.claims:
            if scope in scopes:needed.update(dict(claims))
        return actual == needed and bool(needed)


def seal_scoped_validation(files, panels, rows):
    allowed={(p['source_file_id'],p.get('source_page'),p['panel_code']):p for p in panels}
    by_id={f.id:f for f in files};groups={};revisions={}
    if not rows:return None
    for row in rows:
        scope=(row.get('source_file_id'),row.get('source_page'),row.get('panel_code'))
        panel=allowed.get(scope);region=row.get('evidence_region') or {};observed=row.get('source_observations') or {}
        coverage=observed.get('coverage_review') or {}
        panel_checked = coverage.get('method') == 'whole_panel' and region.get('status') == 'panel_checked'
        if panel is None or not (panel_checked or region.get('status') == 'verified' and row.get('evidence_image')):
            return None
        if region.get('frame') != 'selected_panel' or region.get('source_region') != panel['source_region']:
            return None
        if coverage.get('status') != 'passed' or coverage.get('issues') != [] or coverage.get('read_failed') is not False:
            return None
        if observed.get('evidence_gaps') != [] or not panel_checked and (
                row.get('tag') and region.get('tag_verified') is not True
                or row.get('connected_load') and region.get('load_verified') is not True):
            return None
        file=by_id.get(scope[0]);revision=observed.get('source_revision')
        if file is None or not revision:return None
        if file.id not in revisions:
            path=str(Path(file.file_path).resolve());revisions[file.id]=(path,source_revision(path))
        if revisions[file.id][1] != revision:return None
        groups.setdefault(scope,Counter()).update([claim_key(row)])
    if set(groups) != set(allowed):return None
    return ScopedValidation(tuple((scope,tuple(claims.items())) for scope,claims in groups.items()),
                            tuple((file_id,*value) for file_id,value in revisions.items()))

"""Isolated regression checks: no production reviews, projects or training labels."""
import copy
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from app.services.cad import design_learning as memory
from app.services.cad.project_design_store import save_designs


class DesignLearningTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.path = self.root / '1.json'
        (self.root / 'geometry').mkdir()
        (self.root / ('geometry/' + 'a'*32 + '.json')).write_text('{}')
        self.profiles = [self.profile('A'), self.profile('B')]
        self.patches = [patch.object(memory, 'profile_root', return_value=self.root),
                        patch.object(memory, 'load_profiles', side_effect=lambda: self.profiles)]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)
        self.request = {'category': 'MCB', 'brand': 'ABB', 'poles': 2, 'in_a': 20, 'spec': '2P 20A'}
        self.design = {'id': 'cabinet-1', 'name': 'Fixture', 'state': {
            'templateId': 'shell-1', 'mountingMode': 'panel',
            'sourceForm': {'model': {'dimensions': {'width': 500, 'height': 700, 'depth': 250}}},
            'customDevices': [{'id': 'device-1', 'catalog_profile_id': 'B', 'width': 36, 'height': 80,
                               'front': {'geometry_ref': 'geometry/'+'a'*32+'.json'},
                               'side': {'geometry_ref': 'geometry/'+'a'*32+'.json'},
                               'depth': 70, 'takeoff_requirement': self.request,
                               'geometry_status': 'source_cad_requires_electrical_review'}],
            'placements': [{'id': 'p1', 'sourceId': 'device-1', 'owner': 'mounting_plate',
                            'x': 50, 'y': 50, 'standoff': 0, 'rotation': 0}],
            'diagnostics': {'collisions': []}}}

    def profile(self, ident):
        return {'id': ident, 'name': 'MCB ABB family '+ident+' 2P', 'brand': 'ABB', 'views': [
            {'face': 'front', 'units': 'mm', 'width': 36, 'height': 80, 'geometry_ref': 'geometry/'+'a'*32+'.json'},
            {'face': 'side', 'units': 'mm', 'width': 70, 'height': 80, 'geometry_ref': 'geometry/'+'a'*32+'.json'}]}

    def test_shared_default_layout_is_learned_separately_from_exact_cad(self):
        d = copy.deepcopy(self.design)
        d['state']['sourceForm']['model']['body_dimensions'] = {'width':500,'height':700,'depth':250}
        d['state']['engineeringReport'] = {'policy':'functional-cabinet-v2'}
        d['state']['customDevices'][0].update(geometry_status='parametric_unverified',product={'category':'MCB','poles':2,'in_a':20})
        first=self.save(d)
        self.approve(first,'assembly_layout')
        target=copy.deepcopy(d);target['id']='other-cabinet';target['state']['placements'][0]['x']=90
        path=self.root/'2.json';revision=self.save(target,path=path)
        result=memory.layout_suggestion(path,9,revision,'other-cabinet',[self.path,path])
        self.assertEqual(result['scope'],'assembly_layout')
        self.assertEqual(result['placements'][0]['x'],50)
        self.assertNotEqual(self.match()['items'][0]['status'],'learned')

    def test_default_layout_rejects_nan_and_overlaps(self):
        d=copy.deepcopy(self.design)
        d['state']['sourceForm']['model']['body_dimensions']={'width':500,'height':700,'depth':250}
        d['state']['engineeringReport']={'policy':'functional-cabinet-v2'}
        d['state']['placements'][0]['x']=float('nan')
        with self.assertRaises(ValueError):memory.assembly_evidence(d)
        d['state']['placements'][0]['x']=50
        d['state']['placements'].append({**d['state']['placements'][0],'id':'p2'})
        with self.assertRaises(ValueError):memory.assembly_evidence(d)

    def test_default_layout_does_not_transfer_to_changed_rating(self):
        d=copy.deepcopy(self.design)
        d['state']['sourceForm']['model']['body_dimensions']={'width':500,'height':700,'depth':250}
        d['state']['engineeringReport']={'policy':'functional-cabinet-v2'}
        d['state']['customDevices'][0]['product']={'category':'MCB','poles':2,'in_a':20}
        first=self.save(d);self.approve(first,'assembly_layout')
        target=copy.deepcopy(d);target['id']='other-cabinet';target['state']['customDevices'][0]['product']['in_a']=30
        path=self.root/'2.json';revision=self.save(target,path=path)
        result=memory.layout_suggestion(path,9,revision,'other-cabinet',[self.path,path])
        self.assertEqual(result['status'],'no_compatible_case')

    def test_large_rating_does_not_reuse_a_small_breaker_frame(self):
        self.assertFalse(memory.compatible(self.profiles[0],{**self.request,'in_a':125}))
        profile={**self.profiles[0],'name':'MCCB ABB NSX100 3P'}
        requested={'category':'MCCB','brand':'ABB','poles':3,'in_a':250}
        self.assertFalse(memory.compatible(profile,requested))
        profile['name']='MCCB ABB NSX100/250 3P'
        self.assertTrue(memory.compatible(profile,requested))

    def save(self, design=None, revision='', path=None, owner=9):
        return save_designs(path or self.path, [design or self.design], revision, owner_id=owner, actor_id=owner)['revision']

    def approve(self, revision, scope='device_selection'):
        return memory.approve(self.path, 9, 9, revision, 'cabinet-1', scope, 'Checked fixture geometry')

    def match(self, owner=9, allowed=None, devices=None):
        return memory.recommendations(self.path, owner, devices or [self.request],
                                      [self.path] if allowed is None else allowed)

    def test_only_explicit_approval_changes_ranking(self):
        revision = self.save()
        self.assertEqual(self.match()['items'][0]['candidates'][0]['profile_id'], 'A')
        self.approve(revision)
        result = self.match()['items'][0]
        self.assertEqual(result['status'], 'learned')
        self.assertEqual(result['candidates'][0]['profile_id'], 'B')
        self.assertTrue(result['electrical_verification_required'])

    def test_conflict_has_no_event_or_revision(self):
        revision = self.save()
        design = copy.deepcopy(self.design); design['state']['placements'][0]['x'] = 90
        with self.assertRaises(ValueError):
            self.save(design, 'stale')
        self.assertEqual(memory.read_snapshot(self.path)['revision'], revision)
        self.assertEqual(len(memory.overview(self.path, 9, [self.path])['history']), 1)

    def test_cross_worker_revision_race(self):
        revision = self.save()
        def change(x):
            d = copy.deepcopy(self.design); d['state']['placements'][0]['x'] = x
            try:
                self.save(d, revision)
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(change, [60, 70])), 1)

    def test_before_after_and_legacy_import(self):
        self.path.write_text(json.dumps({'revision': 'old', 'designs': [self.design]}))
        changed = copy.deepcopy(self.design); changed['state']['placements'][0]['x'] = 70
        revision = self.save(changed, 'old')
        with memory.database(self.path) as db:
            event = db.execute('SELECT changes FROM events').fetchone()
            delta = json.loads(event['changes'])[0]
            self.assertEqual(delta['before']['state']['placements'][0]['x'], 50)
            self.assertEqual(delta['after']['state']['placements'][0]['x'], 70)
        self.assertEqual(memory.read_snapshot(self.path)['revision'], revision)

    def test_authoritative_read_survives_json_mirror_failure(self):
        with patch.object(Path, 'replace', side_effect=OSError('fixture failure')):
            revision = self.save()
        self.assertFalse(self.path.exists())
        self.assertEqual(memory.read_snapshot(self.path)['revision'], revision)

    def test_owner_deleted_project_and_revocation(self):
        review = self.approve(self.save())
        self.assertEqual(self.match(owner=10)['active_cases'], 0)
        self.assertEqual(self.match(allowed=[])['active_cases'], 0)
        memory.revoke(self.path, 9, review['review_id'])
        self.assertEqual(self.match()['active_cases'], 0)
        self.assertEqual(self.approve(memory.read_snapshot(self.path)['revision'])['status'], 'revoked')

    def test_retries_do_not_inflate_votes(self):
        revision = self.save()
        first = self.approve(revision)
        self.assertEqual(first, self.approve(revision))
        self.assertEqual(self.match()['items'][0]['candidates'][0]['approved_cases'], 1)
        self.assertEqual(self.save(revision=revision), revision)

    def test_geometry_hash_change_invalidates_review(self):
        self.approve(self.save())
        (self.root / ('geometry/' + 'a'*32 + '.json')).write_text('{"changed":true}')
        self.assertEqual(self.match()['active_cases'], 0)

    def test_edit_invalidates_but_selection_does_not(self):
        revision = self.save(); self.approve(revision)
        selected = copy.deepcopy(self.design); selected['state']['selectedId'] = 'p1'
        revision = self.save(selected, revision)
        self.assertEqual(self.match()['active_cases'], 1)
        selected['state']['placements'][0]['x'] = 65
        self.save(selected, revision)
        self.assertEqual(self.match()['active_cases'], 0)

    def test_requirements_are_not_wildcards(self):
        self.approve(self.save())
        changed = {**self.request, 'in_a': 30, 'spec': '2P 30A'}
        self.assertEqual(self.match(devices=[changed])['items'][0]['status'], 'catalog_proposal')
        self.assertEqual(self.match(devices=[{**self.request, 'brand': 'LS'}])['items'][0]['status'], 'needs_evidence')
        self.assertEqual(self.match(devices=[{**self.request, 'poles': 3}])['items'][0]['status'], 'needs_evidence')
        self.assertEqual(self.match(devices=[{**self.request, 'part_number': 'wrong-model'}])['items'][0]['status'], 'needs_evidence')

    def test_missing_geometry_and_temporary_envelope_cannot_be_approved(self):
        d = copy.deepcopy(self.design); d['state']['customDevices'][0]['geometry_status'] = 'parametric_unverified'
        with self.assertRaises(ValueError):
            self.approve(self.save(d))

    def test_tampered_view_cannot_claim_profile_evidence(self):
        d = copy.deepcopy(self.design)
        d['state']['customDevices'][0]['front']['geometry_ref'] = 'geometry/'+'b'*32+'.json'
        with self.assertRaises(ValueError):
            self.approve(self.save(d))

    def test_two_approval_scopes_do_not_double_vote(self):
        revision = self.save(); self.approve(revision); self.approve(revision, 'layout')
        self.assertEqual(self.match()['items'][0]['candidates'][0]['approved_cases'], 1)

    def test_partial_selection_does_not_require_unreviewed_device(self):
        design = copy.deepcopy(self.design)
        design['state']['placements'].append({'id': 'unreviewed', 'sourceId': 'unverified'})
        revision = self.save(design)
        result = memory.approve(self.path, 9, 9, revision, 'cabinet-1', 'device_selection', 'Checked selected only', ['p1'])
        self.assertEqual(result['status'], 'approved')
        with self.assertRaises(ValueError):
            memory.approve(self.path, 9, 9, revision, 'cabinet-1', 'layout', 'Partial layout not allowed', ['p1'])

    def test_selection_changes_do_not_create_journal_noise(self):
        revision = self.save()
        selected = copy.deepcopy(self.design); selected['state']['selectedIds'] = ['p1']
        self.assertEqual(self.save(selected, revision), revision)
        self.assertEqual(len(memory.overview(self.path, 9, [self.path])['history']), 1)

    def test_order_code_uses_only_its_explicit_published_cad_link(self):
        ident = 'a'*24
        (self.root / 'rows').mkdir()
        candidate = {'id': 'B:variant', 'front': self.design['state']['customDevices'][0]['front'],
                     'side': self.design['state']['customDevices'][0]['side']}
        shard = self.root / 'rows/aa.json'
        shard.write_text(json.dumps({ident: {'product': {'sku': 'ORDER-B', 'brand': 'ABB'}, 'candidates': [candidate]}}))
        request = {**self.request, 'part_number': 'ORDER-B', 'price_row_id': ident}
        self.assertTrue(memory.compatible(self.profiles[1], request))
        self.assertFalse(memory.compatible(self.profiles[0], request))
        self.assertFalse(memory.compatible(self.profiles[1], {**request, 'price_row_id': 'wrong-row'}))

    def test_typed_extraction_supports_pricebook_sku_update(self):
        from app.schemas.ai import ExtractedDeviceSchema
        from app.services.ai.takeoff_pricebook import link_devices
        device = ExtractedDeviceSchema(category='MCB', name='MCB', spec='2P 20A', poles=2, in_a=20)
        choice = {'sku': 'TEST-20', 'brand': 'Fixture', 'price_row_id': 'fixture-only'}
        response = {'candidates': [choice], 'status': 'needs_selection'}
        with patch('app.services.ai.takeoff_pricebook.match_device', return_value=response):
            link_devices([device], rows=[])
        self.assertEqual(device.sku, 'TEST-20')

    def test_routes_check_project_access_before_memory(self):
        import asyncio
        from fastapi import HTTPException
        from unittest.mock import AsyncMock
        from app.api.v1.endpoints import projects
        async def verify():
            with patch.object(projects, 'get_project_or_404', new=AsyncMock(side_effect=HTTPException(404))), patch.object(projects, '_design_file') as file:
                calls = [
                    lambda: projects.design_learning_status(1, object(), object()),
                    lambda: projects.approve_design_learning(1, projects.DesignLearningApproval(revision='r', design_id='c', scope='layout', reason='fixture'), object(), object()),
                    lambda: projects.match_learning_devices(1, projects.DesignLearningMatch(devices=[]), object(), object()),
                    lambda: projects.revoke_design_learning(1, 'r', object(), object()),
                    lambda: projects.suggest_learning_layout(1, projects.DesignLearningLayoutRequest(revision='r', design_id='c'), object(), object()),
                ]
                for call in calls:
                    with self.assertRaises(HTTPException):
                        await call()
                file.assert_not_called()
        asyncio.run(verify())

    def test_layout_overlap_and_bounds_rejected(self):
        for x in [490, -1]:
            d = copy.deepcopy(self.design); d['state']['placements'][0]['x'] = x
            revision = self.save(d, memory.read_snapshot(self.path).get('revision', ''))
            with self.assertRaises(ValueError):
                self.approve(revision, 'layout')
        d = copy.deepcopy(self.design); d['state']['placements'].append({**d['state']['placements'][0], 'id': 'p2'})
        revision = self.save(d, memory.read_snapshot(self.path)['revision'])
        with self.assertRaises(ValueError):
            self.approve(revision, 'layout')

    def test_layout_reuse_requires_exact_context_and_new_target_ids(self):
        self.approve(self.save(), 'layout')
        other = self.root / '2.json'
        d = copy.deepcopy(self.design); d['id'] = 'other'; d['state']['placements'][0].update(id='other-p', x=110)
        revision = self.save(d, path=other)
        suggestion = memory.layout_suggestion(other, 9, revision, 'other', [self.path, other])
        self.assertEqual(suggestion['placements'][0]['id'], 'other-p')
        self.assertEqual(suggestion['placements'][0]['x'], 50)
        d['state']['sourceForm']['model']['dimensions']['depth'] = 300
        revision = self.save(d, revision, path=other)
        self.assertEqual(memory.layout_suggestion(other, 9, revision, 'other', [self.path, other])['status'], 'no_compatible_case')


if __name__ == '__main__':
    unittest.main()

import unittest
from unittest.mock import patch
from fastapi import HTTPException
from app.services.ai.takeoff_regions import sign_scope, confirmed_scope
from app.services.ingestion.cad_source_evidence import audit_cad_ratings


class ScopeConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.panel = {'panel_code':'DB1','source_file_id':7,'source_page':1,'source_region':[.1,.2,.4,.6]}
        self.token = sign_scope(self.panel, 3)
        self.context = {'file_ids':[7], 'takeoff_scope':[{'scope_token':self.token}]}

    def test_reading_without_confirmation_returns_no_scope(self):
        self.assertEqual(confirmed_scope({'file_ids':[7]},3), [])

    def test_confirmed_panel_retains_file_page_region(self):
        panel = confirmed_scope(self.context,3)[0]
        for key,value in self.panel.items(): self.assertEqual(panel[key],value)

    def test_rejects_wrong_project_file_and_tampering(self):
        for context,project in [(self.context,4), ({**self.context,'file_ids':[8]},3),
                                ({**self.context,'takeoff_scope':[{'scope_token':self.token+'x'}]},3),
                                ({**self.context,'takeoff_scope':[{'scope_token':42}]},3)]:
            with self.subTest(context=context,project=project), self.assertRaises(HTTPException) as caught:
                confirmed_scope(context,project)
            self.assertEqual(caught.exception.status_code,422)

    def test_expired_and_duplicate_confirmation_rejected(self):
        with patch('app.services.ai.takeoff_regions.time.time',return_value=10**12):
            with self.assertRaises(HTTPException): confirmed_scope(self.context,3)
        with self.assertRaises(HTTPException):
            confirmed_scope({**self.context,'takeoff_scope':self.context['takeoff_scope']*2},3)

    def test_cad_quote_cannot_change_155_to_150(self):
        evidence={'labels':[{'text':'3tix155/5A'}],'rows':[]}
        bad={'name':'Biến dòng','tag':'CT','evidence':'3tix155/5A','spec':'150/5A'}
        self.assertFalse(audit_cad_ratings(evidence,[bad])['passed'])
        self.assertTrue(audit_cad_ratings(evidence,[{**bad,'spec':'155/5A'}])['passed'])


if __name__=='__main__': unittest.main()

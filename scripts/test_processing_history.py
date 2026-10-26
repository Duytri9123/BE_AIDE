import unittest
from app.services.ai.processing_history import ProcessingHistory


class ProcessingHistoryTests(unittest.TestCase):
    def test_keeps_nested_page_events_in_received_order(self):
        sent = []
        history = ProcessingHistory(sent.append)
        for stage in ('page_selection', 'pdf_context', 'sld_scan', 'pdf_evidence_result'):
            history({'type': 'log', 'stage': stage, 'title': stage})
        self.assertEqual([row['stage'] for row in history.snapshot()], [row['stage'] for row in sent])
        self.assertEqual(len(history.snapshot()), 4)

    def test_normalizes_design_messages_without_storing_result_payload(self):
        history = ProcessingHistory(lambda event: None)
        history({'stage': 'cad', 'message': 'Đang tạo CAD', 'progress': 50})
        history({'type': 'complete', 'result': {'secret': 'large result'}})
        self.assertEqual(len(history.snapshot()), 1)
        self.assertEqual(history.snapshot()[0]['title'], 'Đang tạo CAD')
        self.assertNotIn('result', history.snapshot()[0])

    def test_snapshots_do_not_alias_other_sessions(self):
        first, second = ProcessingHistory(lambda e: None), ProcessingHistory(lambda e: None)
        first({'type': 'log', 'title': 'Phiên 1', 'data': {'page': 1}})
        saved = first.snapshot()
        saved[0]['data']['page'] = 2
        self.assertEqual(first.snapshot()[0]['data']['page'], 1)
        self.assertEqual(second.snapshot(), [])


if __name__ == '__main__':
    unittest.main()

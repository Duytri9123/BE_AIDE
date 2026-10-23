import unittest
from unittest.mock import patch
from app.services.cad import catalogtb_assets as library


class SelectionSnapshotTests(unittest.TestCase):
    def test_batch_keeps_revision_then_next_batch_sees_updates(self):
        first, second = [{'id': 'first'}], [{'id': 'second'}]
        with patch.object(library, '_signature', side_effect=['old', 'new']) as signature, \
             patch.object(library, '_read', side_effect=[first, second]):
            with library.selection_snapshot():
                self.assertIs(library.assets(), first)
                with library.selection_snapshot():
                    self.assertIs(library.assets(), first)
                self.assertIs(library.assets(), first)
            self.assertIs(library.assets(), second)
            self.assertEqual(signature.call_count, 2)

    def test_exception_releases_snapshot(self):
        with patch.object(library, '_signature', return_value='revision'), \
             patch.object(library, '_read', return_value=[]):
            with self.assertRaises(ValueError):
                with library.selection_snapshot():
                    raise ValueError('test')
        self.assertIsNone(library._selection_assets.get())


if __name__ == '__main__':
    unittest.main()

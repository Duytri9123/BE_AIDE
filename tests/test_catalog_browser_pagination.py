from unittest import TestCase
from unittest.mock import patch

from app.services.catalogtb_browser import browser_page


class BrowserPaginationTests(TestCase):
    def setUp(self):
        self.rows = [dict(id=str(i), display=f'Thiết bị {i}', brand='A' if i % 2 else 'B',
                          category='Đo lường', type='Đồng hồ', views=[]) for i in range(53)]
        self.data = dict(items=self.rows, total=53, view_count=60,
                         categories=[dict(name='Đo lường', count=53)], labels={})

    def test_pages_are_bounded_non_overlapping_and_preserve_catalog_counts(self):
        with patch('app.services.catalogtb_browser.browser_data', return_value=self.data):
            pages = [browser_page(skip=i, limit=24) for i in (0, 24, 48)]
        self.assertEqual([len(p['items']) for p in pages], [24, 24, 5])
        self.assertEqual([p['has_more'] for p in pages], [True, True, False])
        self.assertEqual([r['id'] for p in pages for r in p['items']], [r['id'] for r in self.rows])
        self.assertTrue(all(p['catalog_total'] == 53 and 'view_count' not in p for p in pages))
        self.assertEqual(len(self.data['items']), 53)

    def test_filters_search_entire_catalog_before_slicing(self):
        with patch('app.services.catalogtb_browser.browser_data', return_value=self.data):
            found = browser_page(q='thiet bi 51', brand='A', category='Đo lường', limit=24)
            filtered = browser_page(brand='B', skip=24, limit=24)
        self.assertEqual([r['id'] for r in found['items']], ['51'])
        self.assertEqual(found['total'], 1)
        self.assertEqual(filtered['total'], 27)
        self.assertEqual(len(filtered['items']), 3)
        self.assertEqual(found['brands'], ['A', 'B'])

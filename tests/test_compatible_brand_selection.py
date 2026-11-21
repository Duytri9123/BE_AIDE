"""A maker preference replaces only electrically compatible catalog products."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from app.services.ai.compatible_brand_selection import compatible_brand_replacements


def breaker(**overrides):
    return dict(category='MCB', name='MCB', spec='1P 16A 6kA', poles=1,
                in_a=16, icu_ka=6, brand='ABB', part_number='OLD', quantity=2, **overrides)


def product(current=16, icu=10):
    return dict(id='ls-mcb', brand='LS Electric', sku='LS16', item_name='MCB LS16',
                category='MCB', price=120000, specifications={
                    'Số cực':'1P', 'In (A)':str(current), 'Icu (kA)':str(icu)})


class CompatibleBrandTests(unittest.TestCase):
    def test_only_matching_breaker_changes_and_keeps_source_identity(self):
        sources = [breaker(), {'category':'CT','name':'Biến dòng','spec':'40/5A','brand':'EMIC','part_number':'CT40','quantity':3},
                   {'category':'METER','name':'Đồng hồ volt','brand':'Mikro','part_number':'V1'}]
        before = deepcopy(sources)
        with patch('app.api.v1.endpoints.cad_library.manifest', side_effect=AssertionError('CAD forbidden')):
            result, count = compatible_brand_replacements(sources, 'LS', [product()])
        self.assertEqual(count, 1)
        self.assertEqual(result[0]['part_number'], 'LS16')
        self.assertEqual(result[0]['unit_price'], 120000)
        self.assertEqual(result[0]['spec'], sources[0]['spec'])
        self.assertEqual(result[0]['quantity'], 2)
        self.assertEqual(result[0]['source_observations']['quotation_source_identity']['part_number'], 'OLD')
        self.assertEqual(result[1:], sources[1:])
        self.assertEqual(sources, before)

    def test_missing_or_wrong_rating_preserves_entire_row(self):
        for rows in ([], [product(current=32)], [product(icu=4)]):
            source = breaker(unit_price=999, selected_product={'sku':'OLD'})
            result, count = compatible_brand_replacements([source], 'LS', rows)
            self.assertEqual(count, 0)
            self.assertEqual(result, [source])

    def test_incomplete_ratings_do_not_change_brand(self):
        source = {'category':'MCB','name':'MCB','brand':'ABB','part_number':'OLD'}
        result, count = compatible_brand_replacements([source], 'LS', [product()])
        self.assertEqual(count, 0)
        self.assertEqual(result, [source])

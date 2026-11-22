"""A maker preference replaces only electrically compatible catalog products."""
from copy import deepcopy
import unittest
from unittest.mock import patch, AsyncMock
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


    def test_unverified_cached_candidates_never_change_identity(self):
        for candidate in (
            {'brand': 'LS Electric', 'sku': 'GUESSED'},
            {'brand': 'LS Electric', 'sku': 'GUESSED', 'source': 'standard_catalog',
             'auto_selectable': True, 'rating_complete': True},
            {'brand': 'LS Electric', 'sku': 'LS32', 'auto_selectable': True,
             'rating_complete': True, 'requires_confirmation': True,
             'match_kind': 'conditional_alternative'},
        ):
            source = breaker(catalog_candidates={'LS Electric': [candidate]}, unit_price=999)
            result, count = compatible_brand_replacements([source], 'LS', [])
            self.assertEqual((result, count), ([source], 0))


    def test_takeoff_request_keeps_original_until_product_is_verified(self):
        from app.services.ai.takeoff_brand_request import apply_takeoff_brand
        from app.schemas.ai import ExtractedDeviceSchema
        for source in (breaker(), ExtractedDeviceSchema(**breaker())):
            before = deepcopy(source)
            with patch('app.services.ai.quotation_selection.published_rows', return_value=[]):
                self.assertFalse(apply_takeoff_brand(source, 'LS'))
            self.assertEqual(source, before)


def web_product(**overrides):
    return dict(brand='LS Electric', sku='WEB16', technical_url='https://www.ls-electric.com/WEB16',
                technical_evidence='WEB16 1P 16A 10kA', auto_selectable=True, rating_complete=True,
                match_kind='exact', parameters={'poles': 1, 'in_a': 16, 'icu_ka': 10}, **overrides)


class BrandResearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_batch_web_changes_only_verified_matching_rows(self):
        from app.services.ai.compatible_brand_selection import research_brand_replacements
        sources = [breaker(), breaker(tag='Q2'), breaker(tag='Q3')]
        before = deepcopy(sources)

        async def research(devices, *args, **kwargs):
            self.assertTrue(kwargs['requested_brand_only'])
            devices[0].catalog_candidates = {'LS Electric': [web_product()]}
            wrong = web_product()
            wrong['parameters']['in_a'] = 32
            devices[1].catalog_candidates = {'LS Electric': [wrong]}
            devices[2].catalog_candidates = {}

        with patch('app.services.ai.quotation_selection.published_rows', return_value=[]), \
             patch('app.services.ai.connection_pool.ConnectionPoolService.get_ordered_connections', AsyncMock(return_value=[])), \
             patch('app.services.ai.web_device_recommendations.research_device_products', side_effect=research) as lookup:
            result, count = await research_brand_replacements(sources, 'LS', None)
        self.assertEqual(count, 1)
        self.assertEqual(result[0]['part_number'], 'WEB16')
        self.assertIsNone(result[0]['unit_price'])
        self.assertEqual(result[1:], sources[1:])
        self.assertEqual(sources, before)
        self.assertEqual(lookup.call_count, 1)

    async def test_failed_web_lookup_preserves_every_field(self):
        from app.services.ai.compatible_brand_selection import research_brand_replacements
        source = breaker(unit_price=999, selected_product={'sku': 'OLD'})
        with patch('app.services.ai.quotation_selection.published_rows', return_value=[]), \
             patch('app.services.ai.connection_pool.ConnectionPoolService.get_ordered_connections', AsyncMock(return_value=[])), \
             patch('app.services.ai.web_device_recommendations.research_device_products', side_effect=RuntimeError('offline')):
            result, count = await research_brand_replacements([source], 'LS', None)
        self.assertEqual((result, count), ([source], 0))

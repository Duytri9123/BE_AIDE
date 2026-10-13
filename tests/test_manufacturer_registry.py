import unittest
from app.services.ai.manufacturer_registry import (
    canonical_brand, manufacturer_categories, search_portfolios, portfolio_hint,
    official_domains,
    timer_function,
)


class ManufacturerRoutingTests(unittest.TestCase):
    def test_pump_alternation_is_not_generic_delay_or_twin_timer(self):
        rows = search_portfolios('TIMER', 'Timer luân phiên bơm', '220V')
        self.assertIn('Finder', rows)
        self.assertIn('Carlo Gavazzi', rows)
        self.assertNotIn('CHINT', rows)
        self.assertNotIn('Autonics', rows)
        self.assertIn('72-42', rows['Finder'])
        self.assertIn('không có nghĩa', portfolio_hint('TIMER', 'Luân phiên bơm'))

    def test_calendar_and_star_delta_have_different_search_scope(self):
        calendar = search_portfolios('TIMER', 'Timer 24h')
        starter = search_portfolios('TIMER', 'Timer sao tam giác')
        self.assertIn('Hager', calendar)
        self.assertNotIn('Hager', starter)
        self.assertIn('Omron', starter)

    def test_ambiguous_alternation_does_not_invent_pump_control(self):
        self.assertIsNone(timer_function('Timer luân phiên'))
        self.assertEqual('pump_alternation',timer_function('Relay luân phiên','điều khiển hai bơm'))
        self.assertEqual('on_delay',timer_function('Timer trễ đóng'))

    def test_current_transformers_do_not_route_to_breaker_catalogue(self):
        rows = search_portfolios('CT', 'Biến dòng', '63/5')
        self.assertIn('EMIC', rows)
        self.assertIn('LOVATO Electric', rows)
        self.assertNotIn('Shihlin', rows)

    def test_unknown_coverage_is_not_negative_coverage(self):
        ls = manufacturer_categories()['LS Electric']
        self.assertEqual('unknown', ls['other_categories_status'])
        self.assertNotIn('TIMER', ls['categories'])
        self.assertIn('MCCB', ls['categories'])
        self.assertEqual('verified', ls['categories']['CONTACTOR']['status'])

    def test_case_and_alias_do_not_split_the_manufacturer(self):
        for alias in ('ls', 'LS ELECTRIC'):
            self.assertEqual('LS Electric', canonical_brand(alias))
        self.assertEqual('HD Hyundai Electric', canonical_brand('Hyundai'))
        self.assertEqual('LOVATO Electric', canonical_brand('Lovato'))
        self.assertEqual('Weidmüller', canonical_brand('weidmuller'))
        self.assertEqual('Shihlin',canonical_brand('Shihlin Electric'))
        self.assertEqual('Selec',canonical_brand('Selec Controls'))

    def test_official_site_filter_uses_the_expanded_registry(self):
        self.assertIn('emic.com.vn',official_domains('EMIC'))
        self.assertIn('ls-electric.com.vn',official_domains('LS'))
        self.assertEqual((),official_domains('Morele'))

    def test_normalized_category_still_routes_to_its_verified_portfolio(self):
        from app.services.ai.inventory_validation import inventory_kind
        self.assertEqual('SHUNT_TRIP',inventory_kind('SHUNT_TRIP'))
        self.assertIn('IDEC',search_portfolios(inventory_kind('POWER_SUPPLY')))
        self.assertIn('Carlo Gavazzi',search_portfolios(inventory_kind('ALTERNATING_RELAY')))

    def test_equal_phase_lamps_share_search_but_voltage_and_colour_remain_distinct(self):
        from app.services.ai.web_device_recommendations import technical_search_key
        from app.schemas.ai import ExtractedDeviceSchema
        def key(spec):return technical_search_key(ExtractedDeviceSchema(category='LIGHT',name='Đèn báo pha',spec=spec))
        self.assertEqual(key('R'),key('Pha Y'))
        self.assertEqual(key('Đèn báo pha R 220VAC'),key('Đèn báo pha B 220VAC'))
        self.assertNotEqual(key('220VAC'),key('24VDC'))
        self.assertNotEqual(key('220VAC màu đỏ'),key('220VAC màu xanh'))

    def test_written_breaker_type_prefix_does_not_split_equal_ratings(self):
        from app.services.ai.web_device_recommendations import technical_search_key
        from app.schemas.ai import ExtractedDeviceSchema
        first=ExtractedDeviceSchema(category='MCCB',name='M4',spec='MCCB 6A 3P 6KA',poles=3,in_a=6,icu_ka=6)
        second=ExtractedDeviceSchema(category='MCCB',name='M10',spec='6A 3P 6KA',poles=3,in_a=6,icu_ka=6)
        self.assertEqual(technical_search_key(first),technical_search_key(second))


if __name__ == '__main__':
    unittest.main()

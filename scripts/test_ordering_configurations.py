import unittest
from app.services.library_ordering_configurations import ordering_configurations


class OrderingConfigurationsTests(unittest.TestCase):
    def device(self,code):return {'brand':'Schneider Electric','brand_identification_status':'verified','product_code':code}

    def test_documented_coil_codes_are_distinct_ordering_skus_without_fake_price(self):
        rows=ordering_configurations(self.device('LC1F185'))
        by_code={r['sku']:r for r in rows}
        self.assertEqual(set(by_code),{'LC1F185M7','LC1F185M5','LC1F185BD','LC1F185MD'})
        self.assertEqual(by_code['LC1F185BD']['specifications']['Điện áp cuộn hút'],'24 V DC')
        self.assertEqual(by_code['LC1F185M7']['specifications']['Ie AC-3 (≤440 V)'],'185 A')
        self.assertTrue(all('price' not in row and row['price_status']=='not_quoted' for row in rows))

    def test_model_specific_frequency_and_no_unverified_maker_guess(self):
        self.assertNotIn('LC1F265M5',{r['sku'] for r in ordering_configurations(self.device('LC1F265'))})
        self.assertEqual(ordering_configurations({**self.device('LC1F185'),'brand_identification_status':'source_library'}),[])
        self.assertEqual(ordering_configurations({**self.device('LC1F185'),'brand':'LS Electric'}),[])
        self.assertEqual(ordering_configurations(self.device('LC1F1854')),[])


if __name__=='__main__':unittest.main()

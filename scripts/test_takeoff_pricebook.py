import unittest
import asyncio
from unittest.mock import patch
from app.schemas.ai import ExtractedDeviceSchema
from app.services.ai.takeoff_pricebook import match_device, link_devices, public_id
from app.services.ai.procurement_review import build_quotation_rows


class TakeoffPricebookTests(unittest.TestCase):
    def test_comma_separated_current_ratings_are_not_decimal_numbers(self):
        rows=[self.row(brand='CHINT',sku='NXM-630S',item_name='NXM-630S',
                       specifications={'Số cực':'3P','In (A)':'500,630','Icu (kA)':'50'})]
        for current in (500,630):
            result=match_device(self.device(brand='CHINT',part_number='',in_a=current),rows)
            self.assertEqual(result['candidate_count'],1)
            self.assertEqual(result['status'],'needs_selection')
        self.assertEqual(match_device(self.device(brand='CHINT',part_number='',in_a=550),rows)['candidate_count'],0)

    def test_decimal_comma_current_is_preserved(self):
        row=self.row(specifications={'Số cực':'3P','In (A)':'6,3','Icu (kA)':'30'})
        self.assertEqual(match_device(self.device(in_a=6.3),[row])['candidate_count'],1)
        self.assertEqual(match_device(self.device(in_a=6),[row])['candidate_count'],0)
    def row(self, **changes):
        return {**dict(id='row1',brand='Mitsubishi Electric',category='MCCB',
                       item_name='NF125-CV 3P 50A',sku='ORDER-50',price=1622000,
                       specifications={'Số cực':'3P','In (A)':'50','Khả năng cắt và điện áp':'Icu=30kA @230VAC'}), **changes}

    def device(self, **changes):
        return {**dict(category='MCCB',name='MCCB',spec='3P 50A',brand='Mitsubishi Electric',
                       part_number='NF125-CV',poles=3,in_a=50,icu_ka=25,quantity=2), **changes}

    def test_exact_model_and_parameters_link_to_published_row(self):
        result=match_device(self.device(),[self.row(),self.row(id='other',item_name='NF125-CV 4P 50A',specifications={'Số cực':'4P','In (A)':'50'})])
        self.assertEqual(result['status'],'matched')
        self.assertEqual(result['price_row_id'],public_id(self.row()))
        self.assertEqual(result['row']['price'],1622000)

    def test_ambiguity_unknown_brand_and_generic_never_auto_price(self):
        self.assertEqual(match_device(self.device(),[self.row(),self.row(id='supplier2',price=1700000)])['status'],'needs_selection')
        self.assertEqual(match_device(self.device(brand=''),[self.row()])['status'],'needs_selection')
        self.assertEqual(match_device(self.device(part_number=''),[self.row()])['status'],'needs_selection')
        self.assertEqual(match_device(self.device(poles=4),[self.row()])['status'],'not_found')
        self.assertEqual(match_device(self.device(part_number='NF125-C'),[self.row()])['status'],'not_found')

    def test_selected_row_resolves_ambiguity_without_trusting_client_price(self):
        d=self.device(part_number='ORDER-50',selection_source='user_selected',
                      selected_product={'price_row_id':public_id(self.row()),'price':1})
        result=match_device(d,[self.row(),self.row(id='supplier2',price=1700000)])
        self.assertEqual(result['status'],'matched')
        self.assertEqual(result['row']['price'],1622000)

    def test_resolver_and_supplier_identity_use_the_same_published_rows(self):
        from app.services.ai.device_price_resolver import DevicePriceResolver
        with patch('app.services.ai.takeoff_pricebook.published_rows',return_value=[self.row()]):
            result=asyncio.run(DevicePriceResolver.resolve(name='MCCB',category='MCCB',
                brand='Mitsubishi Electric',part_number='NF125-CV',poles=3,in_a=50))
        self.assertEqual(result['price_row_id'],public_id(self.row()))
        self.assertEqual(result['unit_price'],1622000)
        self.assertEqual(match_device(self.device(brand='ABB'),[self.row()])['status'],'not_found')

    def test_voltage_and_icu_conflicts_are_not_priced(self):
        self.assertEqual(match_device(self.device(spec='3P 50A 400V'),[self.row()])['status'],'not_found')
        self.assertEqual(match_device(self.device(icu_ka=50),[self.row()])['status'],'not_found')

    def test_schema_preserves_match_and_quote_uses_device_link_not_sku_map(self):
        d=ExtractedDeviceSchema(**self.device())
        link_devices([d],[self.row()])
        self.assertEqual(ExtractedDeviceSchema(**d.model_dump()).pricebook_match['status'],'matched')
        with patch('app.services.ai.takeoff_pricebook.published_rows',return_value=[self.row()]), patch('app.services.ai.procurement_review.assembly_requirements',return_value=[]):
            result=build_quotation_rows([d],{'NF125-CV':1})
        item=next(r for r in result if r['row_type']=='item')
        self.assertEqual(item['unit_price'],1622000)
        self.assertEqual(item['line_total'],3244000)
        self.assertEqual(item['price_row_id'],public_id(self.row()))


if __name__=='__main__':
    unittest.main()

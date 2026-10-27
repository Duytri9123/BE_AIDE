import json
import unittest
from unittest.mock import AsyncMock
from app.schemas.ai import ExtractedDeviceSchema as Device
from app.services.ai.inventory_validation import count_mismatches, count_panel_with_fallback


def devices(kind, quantity, panel='TĐT'):
    return Device(category=kind, name=kind, spec='', quantity=quantity, panel_code=panel)


class InventoryCountGroups(unittest.IsolatedAsyncioTestCase):
    def test_generic_meter_count_checks_bodies_without_claiming_function(self):
        payload={'counts':[{'panel_code':'TDT','category':'METER','quantity':1}]}
        self.assertEqual(count_mismatches([devices('AMMETER',1)],payload), [])
        self.assertTrue(count_mismatches([devices('AMMETER',2)],payload))
        self.assertTrue(count_mismatches([devices('AMMETER',1,'OTHER')],payload))
        self.assertTrue(count_mismatches([devices('VOLTMETER',1)],
            {'counts':[{'panel_code':'TDT','category':'AMMETER','quantity':1}]}))
    def test_generic_cb_counts_include_specific_breakers(self):
        self.assertEqual(count_mismatches([devices('MCB',19),devices('CB',1)],
            {'counts':[{'panel_code':'TDT','category':'CB','quantity':20}]}), [])

    def test_generic_cb_does_not_hide_missing_spare(self):
        errors=count_mismatches([devices('MCB',19)],
            {'counts':[{'panel_code':'TDT','category':'CB','quantity':20}]})
        self.assertEqual(len(errors),1)
        self.assertIn('bóc tách 19, kiểm đếm nguồn 20',errors[0])

    def test_explicit_subtypes_and_panel_boundaries_remain_constraints(self):
        self.assertTrue(count_mismatches([devices('MCCB',20)],
            {'counts':[{'panel_code':'TDT','category':'MCB','quantity':20}]}))
        self.assertTrue(count_mismatches([devices('MCB',20,'OTHER')],
            {'counts':[{'panel_code':'TDT','category':'CB','quantity':20}]}))

    def test_generic_count_does_not_consume_explicit_subtype_twice(self):
        payload={'counts':[{'panel_code':'TDT','category':'CB','quantity':1},
                           {'panel_code':'TDT','category':'MCB','quantity':19}]}
        self.assertEqual(count_mismatches([devices('MCB',19),devices('MCCB',1)],payload),[])
        self.assertTrue(count_mismatches([devices('MCB',19)],payload))

    async def test_wrong_bom_crop_retries_actual_page(self):
        crop=AsyncMock(return_value=json.dumps({'counts':[{'panel_code':'DB.HT','category':'CB','quantity':0}],
            'uncertain_regions':['Only a BOM is visible']}))
        page=AsyncMock(return_value=json.dumps({'counts':[{'panel_code':'DB.HT','category':'CB','quantity':4}]}))
        result,full_page=await count_panel_with_fallback(crop,page,'Count independently','DB.HT')
        self.assertTrue(full_page)
        self.assertEqual(result['counts'][0]['quantity'],4)
        page.assert_awaited_once()
        self.assertIn('TOÀN BỘ TRANG',page.call_args.args[0])

    async def test_uncertain_full_page_still_blocks(self):
        response=json.dumps({'counts':[{'panel_code':'DB.HT','category':'CB','quantity':0}],
            'uncertain_regions':['Unreadable']})
        with self.assertRaises(ValueError):
            await count_panel_with_fallback(AsyncMock(return_value=response),AsyncMock(return_value=response),'Count','DB.HT')


if __name__ == '__main__': unittest.main()

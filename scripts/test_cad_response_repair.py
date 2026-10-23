import json,unittest
from unittest.mock import AsyncMock
from app.services.ai.cad_response_repair import ensure_cad_response
from app.services.ai.response_parser import ResponseParserService


class CadResponseRepairTests(unittest.IsolatedAsyncioTestCase):
    def envelope(self):
        return {'panels':[{'panel_code':'P','devices':[
            {'category':'MCB','tag':'Q1','name':'Branch','spec':'2P 16A','quantity':2},
            {'category':'LIGHT','tag':'RYB','name':'Lamps','spec':'','quantity':3}]}]}

    async def test_malformed_final_closures_recover_the_entire_inventory(self):
        valid=json.dumps(self.envelope());invalid=valid.replace('}]}]}','}}}]}')
        self.assertEqual(ResponseParserService.parse_device_list(invalid),[])
        repaired=await ensure_cad_response(invalid,AsyncMock(return_value=valid))
        self.assertEqual([(d.tag,d.quantity) for d in ResponseParserService.parse_device_list(repaired)],[('Q1',2),('RYB',3)])

    async def test_json_repair_cannot_change_quantity_or_drop_devices(self):
        valid=json.dumps(self.envelope());invalid=valid.replace('}]}]}','}}}]}')
        altered=self.envelope();altered['panels'][0]['devices'][0]['quantity']=1
        with self.assertRaisesRegex(ValueError,'thay đổi'):
            await ensure_cad_response(invalid,AsyncMock(return_value=json.dumps(altered)))


if __name__=='__main__':unittest.main()

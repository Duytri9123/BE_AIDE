import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from app.schemas.ai import ExtractedDeviceSchema
from app.services.ai.web_device_recommendations import normalize_candidates, research_device_products, priced_source, resolve_grounded_sources

def source():
    return {'success':True,'results':[{'url':'https://manufacturer.example/m1','title':'Datasheet TEST200 TEST250 TEST-LAMP A9F74306'},{'url':'https://supplier.example/m1','title':'Price TEST200'}]}

def product(**changes):
    row = {'brand':'LS','sku':'TEST200','name':'MCCB 200A', 'parameters':{'poles':3,'in_a':200,'icu_ka':85}, 'function_match':True, 'voltage_match':True,'technical_evidence':'3P 200A 85kA at 400V','technical_url':'https://manufacturer.example/m1', 'segment':'High','price_vnd':1000000,'price_url':'https://supplier.example/m1','reason':'Đúng thông số; giá chưa VAT.'}
    row.update(changes)
    return row

def device():
    return ExtractedDeviceSchema(category='MCCB',name='MCCB',spec='3P 200A 85kA',poles=3,in_a=200,icu_ka=85)

class WebRecommendationsTests(unittest.IsolatedAsyncioTestCase):
    def test_model_identity_cannot_come_from_generated_description(self):
        row=product(brand='ABB',sku='SH203-C6',name='MCB ABB SH203-C6')
        search={'results':[{'url':row['technical_url'],'title':'MCB SB200M 6A 3P 10kA'}]}
        self.assertEqual([],normalize_candidates({'candidates':[row]},search,device()))
    def test_other_manufacturers_official_catalogue_cannot_prove_claimed_brand(self):
        d=ExtractedDeviceSchema(category='CT',name='Biến dòng',spec='63/5')
        url='https://webshop.selec.com/au/en/product-details/special-current-transformer-2500-5a'
        search={'results':[{'url':url,'title':'CT','snippet':'EMIC HTS 75/5, claimed by generated answer'}]}
        row=product(brand='EMIC',sku='HTS75',name='Current transformer',technical_evidence='Current transformer 75/5',technical_url=url,parameters={'primary_a':75,'secondary_a':5})
        self.assertEqual([],normalize_candidates({'candidates':[row]},search,d))
    def test_unknown_selector_ratings_cannot_be_automatically_selected(self):
        d=ExtractedDeviceSchema(category='SELECTOR',name='Chuyển mạch vôn kế',spec='')
        row=product(name='Voltmeter selector switch',parameters={})
        result=normalize_candidates({'candidates':[row]},source(),d)[0]
        self.assertFalse(result['auto_selectable'])
        self.assertFalse(result['rating_complete'])
    def test_mcb_for_source_mccb_is_only_a_conditional_alternative(self):
        row=product(name='MCB 3P 200A',technical_evidence='MCB 3P 200A 85kA')
        result=normalize_candidates({'candidates':[row]},source(),device())[0]
        self.assertEqual('conditional_alternative',result['match_kind'])
        self.assertFalse(result['auto_selectable'])
        self.assertIn('MCCB',result['replacement_conditions'][0])
    def test_known_mcb_range_cannot_be_exact_mccb_without_generic_type_word(self):
        d=ExtractedDeviceSchema(category='MCCB',name='CB nhánh',spec='3P 6A 6kA',poles=3,in_a=6,icu_ka=6)
        row=product(brand='Schneider Electric',sku='A9F74306',name='Acti9 iC60N 3P 6A C',technical_evidence='3P 6A Icu 10kA',parameters={'poles':3,'in_a':6,'icu_ka':10})
        result=normalize_candidates({'candidates':[row]},source(),d)[0]
        self.assertEqual('conditional_alternative',result['match_kind'])
        self.assertFalse(result['auto_selectable'])

    def test_rcbo_without_confirmed_residual_rating_cannot_auto_select(self):
        d=ExtractedDeviceSchema(category='RCBO',name='RCBO',spec='2P 16A 30mA 6kA',poles=2,in_a=16,icu_ka=6)
        row=product(name='RCBO',parameters={'poles':2,'in_a':16,'icu_ka':6})
        result=normalize_candidates({'candidates':[row]},source(),d)[0]
        self.assertFalse(result['auto_selectable'])
        row['parameters']['residual_ma']=30
        self.assertTrue(normalize_candidates({'candidates':[row]},source(),d)[0]['auto_selectable'])

    def test_lower_voltmeter_range_is_conditional(self):
        d=ExtractedDeviceSchema(category='VOLTMETER',name='Vôn kế',spec='0-600V')
        row=product(name='Voltmeter',parameters={'voltage_max_v':500})
        result=normalize_candidates({'candidates':[row]},source(),d)[0]
        self.assertEqual(result['match_kind'],'conditional_alternative')
        self.assertFalse(result['auto_selectable'])
        self.assertTrue(result['replacement_conditions'])

    def test_unknown_voltmeter_range_cannot_auto_select(self):
        d=ExtractedDeviceSchema(category='VOLTMETER',name='Vôn kế',spec='0-600V')
        result=normalize_candidates({'candidates':[product(name='Voltmeter',parameters={})]},source(),d)[0]
        self.assertFalse(result['rating_complete'])
        self.assertFalse(result['auto_selectable'])

    async def test_google_redirect_keeps_both_citation_and_destination(self):
        import httpx
        original_client=httpx.AsyncClient
        redirect='https://vertexaisearch.cloud.google.com/grounding-api-redirect/test'
        destination='https://manufacturer.example/m1'
        transport=httpx.MockTransport(lambda request:httpx.Response(302,headers={'location':destination}))
        with patch('httpx.AsyncClient',side_effect=lambda **kwargs:original_client(transport=transport,**kwargs)):
            search=await resolve_grounded_sources({'results':[{'url':redirect,'title':'Datasheet TEST200'}]})
        self.assertEqual(search['results'][0]['url'],destination)
        self.assertEqual(search['results'][0]['grounded_url'],redirect)
        candidate=product(technical_url=redirect)
        result=normalize_candidates({'candidates':[candidate]},search,device())
        self.assertEqual(result[0]['technical_url'],destination)

    def test_canonical_url_does_not_accept_an_unrelated_page(self):
        result=normalize_candidates({'candidates':[product(technical_url='https://www.manufacturer.example/m1/')]},source(),device())
        self.assertEqual(len(result),1)
        self.assertEqual(normalize_candidates({'candidates':[product(technical_url='https://manufacturer.example/invented')]},source(),device()),[])

    async def test_same_breaker_ratings_share_results_despite_spec_format(self):
        d1=device();d2=device();d2.spec='3p 200A-85kA';d2.name='Aptomat nhánh L7'
        connection=SimpleNamespace(provider='google',api_key='test',selected_model='test',quotas={})
        result={**source(),'answer':json.dumps({'candidates':[product()]})}
        with patch('app.services.ai.web_device_recommendations.WebSearchService.search',new=AsyncMock(return_value=result)) as search:
            await research_device_products([d1,d2],[connection])
            self.assertEqual(search.await_count,1)
            self.assertEqual(d1.catalog_candidates,d2.catalog_candidates)

    def test_source_id_avoids_model_fabricated_redirect_url(self):
        row=product(source_id=0,technical_url='https://vertexaisearch.cloud.google.com/grounding-api-redirect/fabricated')
        result=normalize_candidates({'candidates':[row]},source(),device())
        self.assertEqual(result[0]['technical_url'],'https://manufacturer.example/m1')

    def test_invalid_source_id_cannot_create_a_source(self):
        row=product(source_id=50,technical_url='')
        self.assertEqual(normalize_candidates({'candidates':[row]},source(),device()),[])

    def test_pilot_lamp_without_supply_voltage_cannot_auto_select(self):
        d=ExtractedDeviceSchema(category='LIGHT',name='Đèn báo pha R',spec='R')
        row=product(brand='CHINT',sku='TEST-LAMP',name='Đèn báo pha',parameters={'voltage':'230VAC'})
        result=normalize_candidates({'candidates':[row]},source(),d)[0]
        self.assertFalse(result['auto_selectable'])
        self.assertFalse(result['rating_complete'])

    def test_model_price_requires_its_cited_url(self):
        result=normalize_candidates({'candidates':[product(price_url='https://invented.example')]},source(),device())
        self.assertIsNone(result[0]['price'])
        self.assertTrue(result[0]['auto_selectable'])
    def test_insufficient_breaking_capacity_rejected(self):
        self.assertEqual(normalize_candidates({'candidates':[product(parameters={'poles':3,'in_a':200,'icu_ka':35})]},source(),device()),[])
    def test_larger_mccb_is_conditional_and_never_auto_selected(self):
        row=product(sku='TEST250',parameters={'poles':3,'in_a':250,'icu_ka':85})
        result=normalize_candidates({'candidates':[row]},source(),device())
        self.assertEqual(result[0]['match_kind'],'conditional_alternative')
        self.assertFalse(result[0]['auto_selectable'])
        self.assertTrue(result[0]['requires_confirmation'])
        self.assertIn('200A',result[0]['replacement_conditions'][0])
        self.assertEqual(device().in_a,200)

    def test_larger_frame_with_200a_trip_is_exact(self):
        row=product(parameters={'poles':3,'in_a':200,'frame_a':250,'icu_ka':85})
        result=normalize_candidates({'candidates':[row]},source(),device())
        self.assertEqual(result[0]['match_kind'],'exact')

    def test_larger_current_does_not_override_wrong_poles_or_low_icu(self):
        for values in [{'poles':2,'in_a':250,'icu_ka':85},{'poles':3,'in_a':250,'icu_ka':35},{'poles':3,'in_a':160,'icu_ka':85}]:
            self.assertEqual(normalize_candidates({'candidates':[product(parameters=values)]},source(),device()),[])

    def test_uncited_model_and_wrong_function_rejected(self):
        for row in [product(technical_url='https://invented.example'),product(function_match=False)]:
            self.assertEqual(normalize_candidates({'candidates':[row]},source(),device()),[])
    async def test_search_groups_devices_and_keeps_sources(self):
        d1,d2=device(),device()
        result=source(); result['answer']=json.dumps({'candidates':[product()]})
        connection=SimpleNamespace(provider='antigravity',api_key='test',selected_model='test',quotas={})
        with patch('app.services.ai.web_device_recommendations.WebSearchService.search',new=AsyncMock(return_value=result)) as search:
            await research_device_products([d1,d2],[connection],preferred_brand='LS')
            self.assertEqual(search.await_count,1)
            self.assertIn('Hãng yêu cầu LS',search.call_args.args[0])
            self.assertEqual(d1.web_research['status'],'products_found')
            self.assertEqual(d2.catalog_candidates['LS Electric'][0]['price'],1000000)
            self.assertTrue(d1.catalog_candidates['LS Electric'][0]['auto_selectable'])
            self.assertEqual(d1.catalog_candidates['LS Electric'][0]['segment'],'high')
    async def test_transient_search_failure_retries_inside_the_same_takeoff(self):
        d=device()
        result=source();result['answer']=json.dumps({'candidates':[product()]})
        connection=SimpleNamespace(provider='antigravity',api_key='test',selected_model='test',quotas={})
        with patch('app.services.ai.web_device_recommendations.WebSearchService.search',new=AsyncMock(side_effect=[{'success':False,'error':'temporary'},result])) as search, \
             patch('app.services.ai.web_device_recommendations.asyncio.sleep',new=AsyncMock()):
            await research_device_products([d],[connection])
        self.assertEqual(2,search.await_count)
        self.assertEqual('products_found',d.web_research['status'])
        self.assertIn('Catalogue datasheet',search.call_args.args[0])
    def test_price_excerpt_must_name_exact_model(self):
        result={'results':[{'url':'https://supplier.example/m1','title':'Other model','snippet':'1.000.000 VND'}]}
        self.assertIsNone(priced_source(result,'TEST200'))
        result['results'][0]['title']='LS TEST200X'
        self.assertIsNone(priced_source(result,'TEST200'))
        result['results'][0]['title']='LS TEST200'
        self.assertEqual(priced_source(result,'TEST200')['price'],1000000)
        result['results'][0]['snippet']='1.000.000 VND hoặc 2.000.000 VND'
        self.assertIsNone(priced_source(result,'TEST200'))

    def test_energy_meter_is_not_a_dedicated_ammeter(self):
        d=ExtractedDeviceSchema(category='METER',name='Đồng hồ ampe',spec='CT 5A')
        row=product(name='Đồng hồ đo năng lượng kWh',parameters={})
        self.assertEqual(normalize_candidates({'candidates':[row]},source(),d),[])

    async def test_unavailable_visible(self):
        d=device()
        await research_device_products([d],[])
        self.assertEqual(d.web_research['status'],'search_unavailable')

if __name__=='__main__': unittest.main()

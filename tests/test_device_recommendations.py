import json
from pathlib import Path
from types import SimpleNamespace
from app.services.ai.device_recommendations import recommendations

class Catalog:
    brand_index = {'LS': [], 'CHINT': [], 'Morele': []}
    def search_candidates(self, brand, **kwargs):
        rows = {'LS': [], 'CHINT': [dict(ma='T1', n='Timer luân phiên', g=200000), dict(ma='T2', n='Timer trễ', g=100000)], 'Morele': [dict(ma='A1', n='Đồng hồ ampe', g=300000), dict(ma='V1', n='Đồng hồ volt', g=400000)]}
        return rows[brand]

def device(kind, name, **kw):
    return SimpleNamespace(category=kind, name=name, spec='', poles=None, in_a=None, icu_ka=None, **kw)

def test_alternating_timer_does_not_offer_delay_timer_or_force_ls():
    result = recommendations(Catalog(), device('TIMER', 'Timer luân phiên'), 'LS')
    assert 'LS' not in result
    assert [r['sku'] for r in result['CHINT']] == ['T1']
    assert not result['CHINT'][0]['auto_selectable']

def test_ammeter_does_not_offer_voltmeter():
    result = recommendations(Catalog(), device('METER', 'Đồng hồ ampe'), 'LS')
    assert [r['sku'] for r in result['Morele']] == ['A1']

if __name__ == '__main__':
    from app.services.device_catalog_engine import DeviceCatalogEngine
    test_alternating_timer_does_not_offer_delay_timer_or_force_ls()
    test_ammeter_does_not_offer_voltmeter()
    engine = DeviceCatalogEngine.get_instance()
    source = json.loads(Path('../outputs/tdt-cad-test/e2e-fe-20261009/noitru-takeoff.json').read_text(encoding='utf-8'))
    report = []
    for row in source['devices']:
        d = SimpleNamespace(**{k:row.get(k) for k in ['category','name','spec','poles','in_a','icu_ka']})
        options = recommendations(engine, d, 'LS')
        report.append({'tag':row.get('tag'), 'category':d.category,'spec':d.spec,'brands':list(options),'candidates':options})
    Path('../tmp/noitru-device-recommendations.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Function separation: PASS; existing PDF takeoff rows:', len(report))
    print('Rows with catalog suggestions:', sum(bool(r['brands']) for r in report))

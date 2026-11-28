"""Contract checks independent of the deployed catalog database."""
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.cad.device_block_package import draft_block,block_package
from app.services.cad.price_device_projection import price_device_projections


def check():
    product={'id':'abc','sku':'SKU-123','category':'MCB','brand':'ABB'}
    draft=draft_block(product)
    assert draft['geometry_status']=='parametric_unverified'
    assert draft['dimensions_verified'] is False
    assert {v['face'] for v in draft['projections']}=={'front','side','top','back','bottom','left'}
    assert block_package(product,[])['candidates'][0]['price_row_id']=='abc'
    for candidate in [
        {'depth': 0, 'front': {}, 'side': {}},
        {'depth': 75, 'front': {'height': 85}, 'side': {'height': 120}},
        {'depth': 75, 'front': {'height': 85, 'variant_id': 'A'}, 'side': {'height': 85, 'variant_id': 'B'}},
    ]:
        reviewed = block_package(product, [candidate])['candidates'][0]
        assert reviewed['depth'] == 0 and reviewed['projectionOnly'] is True
    views=[{'id':face,'name':face,'dxf':{'path':face}} for face in ['front','side','top','back','bottom']]
    record={'cad':{'views':views}}
    from app.services.customer_equipment_information import public_view_id
    detail={'product':product,'cad_devices':[{'id':'device','selection_id':'selection','display':'test',
          'link_scope':'reviewed_family_configuration','views':[{'id':public_view_id(v['id'])} for v in views]}]}
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as directory:
        source=Path(directory)/'face.dxf';source.write_text('source')
        geometry={'paths':[[[0,0],[20,0],[20,30],[0,30],[0,0]]],'width':20,'height':30,'units':'mm'}
        with patch('app.services.cad.price_device_projection.price_row_detail',return_value=detail), \
             patch('app.services.cad.price_device_projection.get_equipment',return_value=record), \
             patch('app.services.cad.price_device_projection.face_code',side_effect=lambda face:face), \
             patch('app.services.cad.price_device_projection._catalogtb_asset',return_value=source), \
             patch('app.services.cad.price_device_projection._projection',return_value=geometry):
            result=price_device_projections('abc',[],[])
    assert result['geometry_status']=='source_cad'
    candidate=result['candidates'][0]
    assert {v['face'] for v in candidate['projections']}=={'front','side','top','back','bottom'}
    assert candidate['front']['paths']==geometry['paths']
    assert candidate['top']['paths']==geometry['paths']
    print('Device block contract checks passed')


if __name__=='__main__':check()

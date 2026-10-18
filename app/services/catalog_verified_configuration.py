"""Do not turn a multi-model drawing legend into an unsupported exact product.

Pole availability checked against Mitsubishi WS-V manufacturer catalog tables.
"""
from .catalog_product_sections import device_poles
from .ai.manufacturer_registry import canonical_brand

DOCUMENT='https://dl.mitsubishielectric.com/dl/fa/document/catalog/lvcb/yn-c-0720/y0720c1609.pdf'
SHARED_FOUR_POLE_FRAMES={'NF125-CV':125,'NF250-CV':250,'NF400-CW':400,
                         'NF630-CW':630,'NF800-CEW':800}

def apply_verified_configuration(profile):
    model=profile.get('product_code')
    if canonical_brand(profile.get('brand'))!='Mitsubishi Electric' or device_poles(profile)!='4P':return False
    if model not in SHARED_FOUR_POLE_FRAMES:return False
    observed=(profile.get('source_identification') or {}).get('source_models_read') or []
    if len(set(observed))<2:return False
    frame=SHARED_FOUR_POLE_FRAMES[model]
    profile['product_code']=None
    profile['display']=f'MCCB Mitsubishi {frame}AF · 4P'
    profile['spec_hint']=f'4P · {frame} AF'
    profile['auto_select']=False;profile['needs_review']=True
    profile['ordering_configurations']=[]
    profile.pop('catalog_reference',None)
    # Retain known type, frame and poles; never transfer a 3P rating into 4P.
    profile['spec']={'so_cuc':'4P','co_khung':f'{frame} AF'}
    references=profile.get('catalog_references') or {}
    profile['catalog_references']={**references,'options':[o for o in references.get('options',[])
        if o.get('model') not in SHARED_FOUR_POLE_FRAMES]}
    profile['model_configuration_review']={'status':'shared_model_legend',
        'document':DOCUMENT,'previous_model':model}
    return True

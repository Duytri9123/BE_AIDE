"""Repair dangling default resource pointers after a 2D DXF resource import."""

def repair_invalid_layer_resources(doc):
    changed=0
    global_material=doc.materials.get('Global').dxf.handle
    normal=doc.rootdict['ACAD_PLOTSTYLENAME']['Normal'].dxf.handle
    for layer in doc.layers:
        for attribute,kind,default in (
            ('material_handle','MATERIAL',global_material),
            ('plotstyle_handle','ACDBPLACEHOLDER',normal),
        ):
            handle=layer.dxf.get(attribute)
            entity=doc.entitydb.get(handle) if handle else None
            if handle and (entity is None or entity.dxftype()!=kind):
                layer.dxf.set(attribute,default);changed+=1
    return changed

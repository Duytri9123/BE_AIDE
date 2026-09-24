"""Server-side grouping keeps paging independent of SKU/view duplication."""
from collections import defaultdict
from app.services.cad.device_families import build_families
from app.services.cad.library_taxonomy import classify, normalize


def browse_rows(models, assets):
    families = build_families(assets)
    by_asset = {a: f for f in families for a in f['asset_ids']}
    asset_lookup = {a['id']: a for a in assets}
    groups = defaultdict(list)
    for model in models:
        params = model.parameters or {}
        asset_id = (params.get('cad') or {}).get('asset_id')
        if not asset_id and model.sku.startswith('CAD:'): asset_id = model.sku[4:]
        # Source tables are references, not purchasable devices or individual views.
        if asset_lookup.get(asset_id, {}).get('is_collection'): continue
        family = by_asset.get(asset_id)
        if asset_id and not family: continue
        dimensions = model.dimensions or {}
        if family:
            key = 'cad:' + family['id']
        elif all(dimensions.get(k) for k in ('w', 'h', 'd')):
            key = repr((model.device_series_id, params.get('p'), *(dimensions[k] for k in ('w', 'h', 'd'))))
        else:
            key = f'model:{model.id}'
        groups[key].append((model, family))
    rows = []
    for key, members in groups.items():
        model, family = members[0]
        series = model.series
        category = series.category.name if series and series.category else ''
        classification = classify(model.name, category)
        rows.append(dict(key=key, model=model, family=family, members=[m for m, _ in members],
                         name=family['name'] if family else model.name,
                         kind=family['kind'] if family else classification['kind'],
                         group=family['group'] if family else classification['group']))
    return rows

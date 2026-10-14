"""Inspect every public equipment profile, its view files and commercial choices.

This validates links/files/SVG structure, not visual engineering equivalence.
"""
import json
import math
import sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit,unquote
from xml.etree import ElementTree

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.services.catalogtb_browser import browser_data
from app.services.equipment_library import asset_bytes
from app.api.v1.endpoints.equipment_library import _cad_view_file
from app.services.ai.takeoff_pricebook import published_rows
from app.services.library_price_matching import configuration_links,device_price_diagnostic


def audit():
    data=browser_data();prices=published_rows();records=[];seen=set();views=0
    for device in data['items']:
        issues=[];view_ids=[v['id'] for v in device['views']]
        if device['id'] in seen:issues.append('duplicate_device_id')
        seen.add(device['id'])
        if not view_ids:issues.append('missing_views')
        if device.get('primary_view') not in view_ids:issues.append('invalid_primary_view')
        if len(view_ids)!=len(set(view_ids)):issues.append('duplicate_view_id')
        for view in device['views']:
            views+=1
            try:
                parts=urlsplit(view['preview']).path.strip('/').split('/')
                if len(parts)!=5 or parts[0]!='equipment-library' or parts[2]!='views':raise ValueError('Invalid preview route')
                cid,vid=unquote(parts[1]),unquote(parts[3])
                path=_cad_view_file(cid,vid,'preview')
                content=asset_bytes(path)
                if path.lower().endswith('.svg'):
                    svg=ElementTree.fromstring(content)
                    bounds=[float(v) for v in svg.attrib.get('viewBox','').replace(',',' ').split()]
                    if len(bounds)!=4 or not all(math.isfinite(v) for v in bounds) or min(bounds[2:])<=0:raise ValueError('Invalid SVG bounds')
            except Exception as exc:issues.append('preview:'+view['id']+':'+type(exc).__name__)
            try:
                parts=urlsplit(view['download']).path.strip('/').split('/')
                if len(parts)!=5 or parts[4]!='dxf':raise ValueError('Invalid DXF route')
                _cad_view_file(unquote(parts[1]),unquote(parts[3]),'dxf')
            except Exception as exc:issues.append('dxf:'+view['id']+':'+type(exc).__name__)
        links=configuration_links(device,prices)
        records.append({'id':device['id'],'name':device.get('display'),'brand':device.get('brand'),
                        'manufacturer_status':device.get('brand_identification_status'),
                        'product_code':device.get('product_code'),'type':device.get('type'),
                        'view_count':len(view_ids),'price_choice_count':len(links),
                        'price_diagnostic':device_price_diagnostic(device['id']),'structural_issues':issues})
    return {'checked_at':datetime.now(timezone.utc).isoformat(),'checked_devices':len(records),'checked_views':views,
            'linked_devices':sum(bool(r['price_choice_count']) for r in records),
            'devices_with_structural_issues':sum(bool(r['structural_issues']) for r in records),
            'manufacturer_status_counts':dict(Counter(r['manufacturer_status'] for r in records)),
            'review_scope':'All public devices: identity metadata, view routes, source files, SVG bounds and published price links. Not visual/engineering approval.',
            'items':records}


if __name__=='__main__':
    result=audit()
    (ROOT/'docs/library-complete-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='items'},ensure_ascii=False))
    for item in result['items']:
        if item['structural_issues']:print(item['id'],item['name'],item['structural_issues'])

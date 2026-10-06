"""Deterministic, CAD-only selection layer over the preserved source inventory."""
from build_tudien_v2 import *
from ezdxf.lldxf.tagwriter import TagCollector

# Reviewed source views have unperforated electrical door faces. Mechanical lock,
# hinge and enclosure ventilation features are intentionally retained.
BLANK_DOOR_FORMS={'formtu-22198','formtu-3115f','formtu-d86ed','formtu-d8a73',
 'formtu-129c0b','formtu-12ad97','formtu-14e8b3','formtu-15e13d','formtu-15e624',
 'formtu-15e84f','formtu-15efcc','formtu-2416ba','formtu-2618d5','formtu-27d4c6',
 'formtu-27d8b9','formtu-27e0a1','formtu-27f9bd','formtu-2c382d','formtu-2c420d','formtu-2ce458'}
FACES={'mat_truoc':'front','mat_hong':'side','mat_tren':'top','mat_sau':'rear',
       'chua_xac_dinh':'unknown','mat_day':'bottom'}

def fingerprint(path):
    doc=ezdxf.readfile(path);rows=[]
    def value(v):
        if isinstance(v,float):return round(v,5)
        if isinstance(v,(tuple,list)) or v.__class__.__name__ in ('Vec2','Vec3'):return [value(x) for x in v]
        return v
    for e in doc.modelspace():
        tags=[(t.code,value(t.value)) for t in TagCollector.dxftags(e) if t.code not in (5,105,330,360,8,62,420,430)]
        rows.append(json.dumps(tags,sort_keys=True,default=str))
    return hashlib.sha256(json.dumps(sorted(rows)).encode()).hexdigest()

def main():
    snapshot=OUT/'nguon/catalog_tong_hop_truoc_loc.json'
    if not snapshot.exists():shutil.copyfile(OUT/'catalog.json',snapshot)
    source=load(snapshot);assets=source['cad_assets'];by_id={a['id']:a for a in assets}
    device_reviews=load(Path(__file__).with_name('tudien_v2_reviewed_devices.json'))
    declared_units={}
    for manifest in (DATA/'device_layouts').glob('*/manifest.json'):
        for item in load(manifest)['items']:
            if item.get('units')=='mm':declared_units['lib_'+item['id']]=manifest.relative_to(DATA).as_posix()
    cache_path=OUT/'nguon/geometry_fingerprint_cache.json'
    cache=load(cache_path) if cache_path.exists() else {}
    review=[];alias={};canonical={};physical={}
    for i,a in enumerate(assets):
        a['view']=FACES.get(a['view'],a['view'])
        if a['id'] in device_reviews:
            r=device_reviews[a['id']];a['view']=r['view'];a['view_review']=r
            if r.get('poles'):a['poles']=r['poles']
        a['millimeter_basis']='DXF_INSUNITS_4' if a['geometry']['units_code']==4 else declared_units.get(a['id'])
        if a['id'] in {'lib_2b69d9346c524d2036a2','lib_eb6a7828c68bfda38d24','lib_f14d234fa86819d3dd54'}:
            a['millimeter_basis']='reviewed_model_front_exact_W_H_match_to_supplied_catalog; source INSUNITS inch header inconsistent with 75x130/105x165/140x257 geometry'
            a['unit_header_correction']={'original':a['geometry']['units_code'],'new':4,'coordinate_scale':1,'basis':a['millimeter_basis']}
        path=OUT/a['cad'];digest=hashlib.sha256(path.read_bytes()).hexdigest()
        fp=cache.get(digest) or fingerprint(path);cache[digest]=fp;a['geometry_fingerprint']=fp
        # Same geometry may be shared without claiming same manufacturer/model.
        physical.setdefault(fp,a['cad']);a['shared_geometry_cad']=physical[fp]
        identity=(a['kind'],a['category'],a['manufacturer'],norm(a['name']).strip(),a['view'],a.get('poles'),fp)
        if identity in canonical:
            alias[a['id']]=canonical[identity]['id']
            canonical[identity].setdefault('source_aliases',[]).append({'id':a['id'],'metadata':a['metadata']})
        else:canonical[identity]=a;alias[a['id']]=a['id']
        if i%400==0:print('Fingerprint',i,flush=True)
    save(cache_path,cache)
    canon={a['id']:a for a in canonical.values()}
    forms=[]
    for form in source['forms']:
        a=by_id[form['id']]
        sid=a['evidence'].get('source_sheet')
        if sid not in BLANK_DOOR_FORMS:
            review.append({'id':a['id'],'reason':'door_cutouts_or_incomplete_dimensions_or_special_purpose_form','metadata':a['metadata']});continue
        dims=a['dimensions_mm_from_source_title'];attrs=a['evidence']['title_attributes'];desc=norm(' '.join(attrs.values()))
        environment='ngoai_troi' if 'NGOAI TROI' in desc else 'trong_nha' if 'TRONG NHA' in desc else None
        door_layers=2 if re.search(r'2 LOP CANH|HAI LOP CANH',desc) else 1 if '1 LOP CANH' in desc else None
        dimensions_in_06=bool(re.fullmatch(r'\s*\d{3,4}\s*[xX×]\s*\d{3,4}\s*[xX×]\s*\d{3,4}\s*',attrs.get('#06','')))
        thickness=attrs.get('#08') if dimensions_in_06 else attrs.get('#09')
        if not environment or not door_layers or not thickness:
            review.append({'id':a['id'],'reason':'missing_environment_door_layers_or_sheet_thickness','metadata':a['metadata']});continue
        a['specifications']={'height_mm':dims['height'],'width_mm':dims['width'],'depth_mm':dims['depth'],
          'sheet_thickness_source':thickness.strip() if thickness else None,'environment':environment,
          'door_layers':door_layers,'ip_rating':None,'material_grade':None,'technical_standard_certification':None,
          'source_title_attributes':attrs}
        a['door_policy']={'equipment_cutouts':[],'inner_door_equipment_cutouts':[],
          'status':'blank_for_equipment_layout','mechanical_features_retained':True,
          'cutouts_created_only_after':'equipment placement and specific manufacturer cutout dimensions approved'}
        a['selection_status']='usable_source_shell_fixed_dimensions'
        a['millimeter_basis']='FOMTU title HxWxD with original extraction metadata in millimeters'
        a['unit_header_correction']={'original':a['geometry']['units_code'],'new':4,'coordinate_scale':1,'basis':a['millimeter_basis']}
        a['auto_resize']=False
        spec=f"{dims['height']}x{dims['width']}x{dims['depth']}"
        a['standard_name']='Vỏ tủ '+('ngoài trời' if environment=='ngoai_troi' else 'trong nhà' if environment else 'chưa xác định môi trường')+' '+spec+' mm'+(f' · {door_layers} lớp cánh' if door_layers else '')
        a['name']=a['standard_name'];a['form_code']='VT-'+slug(environment or 'CXN')+'-'+spec+'-'+slug(thickness or 'CXN')+'-'+str(door_layers or 'CXN')+'L'
        a['deduplication_key']=a['form_code']+'-'+a['geometry_fingerprint'][:12]
        forms.append(a)
    # Enforce one canonical asset for a face. Conflicting drawings are quarantined,
    # never selected with next()/random order.
    products=[];product_review=[];used=set();collisions=[]
    for p in source['products']:
        choices=collections.defaultdict(dict)
        for link in p.get('cad_links',[]):
            aid=alias[link['asset_id']];a=canon[aid]
            if a['view'] not in ('front','side','top','rear','bottom'):continue
            if a['kind']!='thiet_bi' or a['manufacturer']!=p['manufacturer']:continue
            ap=a.get('poles')
            if ap and p['specifications'].get('p') and int(str(ap).replace('P',''))!=p['specifications']['p']:continue
            s=p['specifications'];b=a['geometry']['drawing_extent']
            expected={'front':(s.get('w'),s.get('h')),'rear':(s.get('w'),s.get('h')),
                      'side':(s.get('d'),s.get('h')),'top':(s.get('w'),s.get('d')),'bottom':(s.get('w'),s.get('d'))}[a['view']]
            if not a['millimeter_basis'] or not all(expected):continue
            if max(abs(b['width']-expected[0]),abs(b['height']-expected[1]))>1:continue
            choices[a['view']][a['geometry_fingerprint']]=a
        if 'front' not in choices or any(len(v)>1 for v in choices.values()):
            reason='conflicting_same_face_drawings' if any(len(v)>1 for v in choices.values()) else 'no_verified_front_with_matching_catalog_dimensions'
            product_review.append({**p,'selection_status':'excluded','reason':reason})
            if reason.startswith('conflicting'):collisions.append(p['id'])
            continue
        selected={face:next(iter(options.values()))['id'] for face,options in choices.items()}
        p['cad_by_face']=selected;p['cad_links']=[{'asset_id':aid,'face':face,'cad':canon[aid]['cad'],'preview':canon[aid]['preview'],
          'status':'catalog_series_brand_face_dimensions_consistent','approved_for_manufacture':False} for face,aid in selected.items()]
        p['selection_status']='usable_for_source_cad_layout';p['cad_status']='has_cad';products.append(p);used.update(selected.values())
    accessories=[]
    for a in canon.values():
        if a['kind']!='phu_kien':continue
        if a['view'] not in ('front','side','top','rear','bottom','section') or not a['millimeter_basis']:
            review.append({'id':a['id'],'reason':'accessory_view_or_units_unresolved','metadata':a['metadata']});continue
        a['selection_status']='explicit_asset_only';a['automatic_substitution']=False
        a['specifications']={'drawing_width_mm':a['geometry']['drawing_extent']['width'],
          'drawing_height_mm':a['geometry']['drawing_extent']['height'],'source_name':a['name'],
          'manufacturer':None if a['manufacturer']=='chua_xac_dinh' else a['manufacturer'],
          'dimension_basis':'source_geometry_not_nominal_catalog_size'}
        accessories.append(a);used.add(a['id'])
    accessory_groups=collections.defaultdict(list)
    for a in accessories:
        base=norm(a['name'])
        if base.startswith('HL036'):base='HL036'
        elif base.startswith('HL003-2'):base='HL003-2'
        else:base=re.sub(r'[- ]?(FRONT|SIDE|TOP|REAR|BOTTOM)$','',base).strip()
        a['component_key']=a['category']+'|'+a['manufacturer']+'|'+base
        accessory_groups[(a['component_key'],a['view'])].append(a)
    accessories=[]
    for key,group in accessory_groups.items():
        if len({a['geometry_fingerprint'] for a in group})>1:
            for a in group:
                used.discard(a['id']);review.append({'id':a['id'],'reason':'same_component_face_different_geometry','component_face':key,'metadata':a['metadata']})
        else:
            selected=sorted(group,key=lambda a:a['id'])[0]
            accessories.append(selected)
            for a in group:
                if a['id']!=selected['id']:used.discard(a['id'])
    used.update(a['id'] for a in forms)
    active_assets=[a for a in canon.values() if a['id'] in used]
    components={}
    for a in accessories:
        components.setdefault(a['component_key'],{'name':a['component_key'].split('|')[-1],'category':a['category'],
          'manufacturer':a['manufacturer'],'cad_by_face':{},'automatic_substitution':False})['cad_by_face'][a['view']]=a['id']
    active={'schema_version':3,'name':'Catalog CAD đang sử dụng','policy':{'cad_required':True,'unknown_items_auto_select':False,
      'one_asset_per_product_face':True,'ambiguous_face':'reject','inner_door':'no_equipment_cutouts_before_layout',
      'standards':'Internal naming and data requirements only. No IEC/IP certification claimed without evidence.'},
      'forms':forms,'products':products,'cad_assets':active_assets,'accessory_products':accessories,'accessory_components':list(components.values()),'quotation_products':[]}
    # Only current assets remain in the browsable folders. Source copies remain
    # reachable through the snapshot and explicit quarantine manifest.
    for a in active_assets:
        old_folder=(OUT/a['cad']).parent
        folder=OUT/'dang_su_dung'/a['kind']/(slug(a.get('form_code') or a['category']))/slug(a['manufacturer'])/a['id']
        folder.mkdir(parents=True,exist_ok=True)
        for field in ['cad','preview','reference_cad']:
            if not a.get(field):continue
            src=OUT/a[field];dest=folder/src.name
            if not dest.exists():shutil.copyfile(src,dest)
            if field=='cad' and a.get('unit_header_correction'):
                doc=ezdxf.readfile(dest)
                if doc.units!=4:doc.units=4;doc.saveas(dest)
            a[field]=dest.relative_to(OUT).as_posix()
        a['metadata']=(folder/'metadata.json').relative_to(OUT).as_posix()
    active_index={a['id']:a for a in active_assets}
    for p in products:
        for link in p['cad_links']:
            a=active_index[link['asset_id']];link['cad']=a['cad'];link['preview']=a['preview']
        p['metadata']='dang_su_dung/san_pham/'+slug(p['manufacturer'])+'/'+slug(p['id'])+'.json'
        save(OUT/p['metadata'],p)
    save(OUT/'catalog.json',active)
    save(OUT/'cho_doi_chieu/san_pham_chua_du_dieu_kien.json',product_review)
    save(OUT/'cho_doi_chieu/khong_tu_dong_su_dung.json',review)
    save(OUT/'geometry_aliases.json',alias)
    save(OUT/'geometry_store.json',physical)
    save(OUT/'form_tu/index.json',forms)
    save(OUT/'thiet_bi/index.json',[a for a in active_assets if a['kind']=='thiet_bi'])
    save(OUT/'phu_kien/index.json',accessories)
    for a in active_assets:save(OUT/a['metadata'],a)
    selected_paths={(OUT/a['metadata']).parent.resolve() for a in active_assets}
    active_root=(OUT/'dang_su_dung').resolve()
    for meta in list(active_root.rglob('metadata.json')):
        folder=meta.parent.resolve()
        if folder in selected_paths:continue
        destination=(OUT/'cho_doi_chieu/ban_active_truoc'/folder.relative_to(active_root)).resolve()
        if destination.exists():destination=destination.with_name(destination.name+'_'+hid(str(meta.stat().st_mtime_ns)))
        if not folder.is_relative_to(active_root) or not destination.is_relative_to((OUT/'cho_doi_chieu').resolve()):raise ValueError('Unsafe archival path')
        destination.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(folder),str(destination))
    summary={'catalog_products':len(products),'cad_assets':len(active_assets),'by_kind':dict(collections.Counter(a['kind'] for a in active_assets)),
      'empty_shell_multi_view_sets':len(forms),'empty_shell_other_view_assets':0,'duplicate_aliases':sum(k!=v for k,v in alias.items()),
      'source_assets_reviewed_structurally':len(assets),'products_excluded':len(product_review),'conflicting_products':collisions}
    save(OUT/'active_summary.json',summary)
    db={'active':True,'summary':summary,'assets':active_assets,'products':products,'accessory_products':accessories,'quotation_products':[]}
    page=Path(__file__).with_name('tudien_v2_browser.html').read_text(encoding='utf8')
    page=page.replace('__DATA__',json.dumps(db,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c'))
    (OUT/'index.html').write_text(page,encoding='utf8')
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()

"""Public display metadata from CatalogTB only, without filesystem paths."""
import ast,hashlib,json,re
import time
import unicodedata
from threading import Lock, Thread
import logging
from pathlib import Path
from urllib.parse import unquote,quote
from .equipment_library import CATALOG_TB_ROOT

_cache = None
_cache_until = 0
_cache_root = None
_cache_lock = Lock()


def catalog_query_matches(query, text):
    """Match reordered words and punctuation variants of product identifiers."""
    def normalize(value):
        return ''.join(c for c in unicodedata.normalize('NFD', str(value).casefold())
                       if not unicodedata.combining(c)).replace('đ', 'd')
    query, text = normalize(query), normalize(text)
    if query in text and not re.search(r'\d', query):
        return True
    # Keep model numbers attached: NDK-25 matches NDK25, not NDK250.
    compact = lambda value: re.sub(r'(?<=\w)[\-_/](?=\w)', '', value)
    terms = re.findall(r'\w+', compact(query))
    words = re.findall(r'\w+', compact(text))
    def match_term(term):
        if term in words:
            return True
        # A catalog family may omit an alphabetic ordering suffix, while its
        # numeric frame must stay intact (NSX100 -> NSX100N, never NSX1000).
        return any(word.startswith(term) and len(word)>len(term) and
                   term[-1].isdigit() and word[len(term)].isalpha() for word in words)
    return bool(terms) and all(match_term(term) for term in terms)


def _snapshot_path():
    return CATALOG_TB_ROOT / '_agent_index' / 'browser_display_v5.json'


def _refresh_browser_data(root):
    global _cache, _cache_until
    try:
        data = _build_browser_data()
        path = _snapshot_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        pending = path.with_suffix('.tmp')
        pending.write_text(json.dumps(data, ensure_ascii=False), encoding='utf8')
        pending.replace(path)
        with _cache_lock:
            if _cache_root == root:
                _cache = data
                _cache_until = time.monotonic() + 300
    except Exception:
        logging.getLogger(__name__).exception('Unable to refresh CAD display snapshot')


def browser_data():
    """Serve a persisted display index; refresh expired records off the request path."""
    global _cache, _cache_until, _cache_root
    with _cache_lock:
        if _cache_root != CATALOG_TB_ROOT:
            _cache = None
            _cache_root = CATALOG_TB_ROOT
            _cache_until = 0
        if _cache is None:
            try:
                _cache = json.loads(_snapshot_path().read_text(encoding='utf8'))
                if not isinstance(_cache.get('items'), list):
                    _cache = None
            except (OSError, ValueError, AttributeError):
                _cache = None
            if _cache is None:
                _cache = _build_browser_data()
                path = _snapshot_path()
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(_cache, ensure_ascii=False), encoding='utf8')
                _cache_until = time.monotonic() + 300
        if time.monotonic() >= _cache_until:
            _cache_until = time.monotonic() + 300
            Thread(target=_refresh_browser_data, args=(CATALOG_TB_ROOT,), daemon=True).start()
        return _cache


def browser_page(q='', category='', brand='', skip=0, limit=24):
    data = browser_data()
    def normalize(value):
        return ''.join(c for c in unicodedata.normalize('NFD', str(value).lower())
                       if not unicodedata.combining(c)).replace('đ', 'd')
    query = normalize(q.strip())
    reference_candidates = None
    if len(query) >= 2 and re.search(r'\d', query):
        from .ai.takeoff_pricebook import published_rows
        from .library_reference_prices import price_index
        reference_candidates = price_index([row for row in published_rows()
            if catalog_query_matches(query, ' '.join(str(row.get(k) or '') for k in ('brand','sku','item_name','specifications')))])
    def matches(item):
        identity = normalize(' '.join(str(item.get(k) or '') for k in
                                     ('display', 'type', 'category', 'product_code')) +
                             ' ' + ' '.join(item.get('search_aliases') or []))
        if query == 'ct':
            return bool(re.search(r'bien dong|biendong|current transformer|\bct\b|\bzct\b', identity))
        if query == 'a':
            return bool(re.search(r'ampe|ammeter|dong ho.*dong dien', identity))
        if query == 'v':
            return bool(re.search(r'volt|von ke|dong ho.*dien ap', identity))
        reference_text = ' '.join(' '.join(str(option.get(k) or '') for k in
            ('brand', 'model')) for option in
            (item.get('catalog_references') or {}).get('options', []))
        if catalog_query_matches(query, identity + ' ' + str(item.get('brand') or '') + ' ' + reference_text):
            return True
        if reference_candidates:
            from .library_reference_prices import reference_rows
            return bool(reference_rows(item, reference_candidates))
        return False
    rows = [p for p in data['items'] if (not category or p.get('category') == category)
            and (not brand or p.get('brand') == brand
                 or brand in {o['brand'] for o in (p.get('catalog_references') or {}).get('options', [])}
                 or (brand == '__generic__' and p.get('brand_kind') == 'generic')
                 or (brand == '__unidentified__' and p.get('brand_kind') == 'unidentified_equipment')) and (not query or matches(p))]
    if query:
        # A match on the drawing's own name/model precedes a selectable reference.
        # Stable sorting keeps the library order within each evidence level.
        rows.sort(key=lambda item: not catalog_query_matches(query, ' '.join(
            str(item.get(k) or '') for k in ('display','product_code','brand','type','category'))))
    display_data={key:value for key,value in data.items() if key!='view_count'}
    return {**display_data, 'items': rows[skip:skip+limit], 'total': len(rows),
            'catalog_total': data['total'], 'skip': skip, 'limit': limit,
            'has_more': skip + limit < len(rows),
            'brands': sorted({p['brand'] for p in data['items'] if p.get('brand')} |
                             {o['brand'] for p in data['items'] for o in (p.get('catalog_references') or {}).get('options', [])
                              if o['brand'] and o['brand'] != 'Chưa xác định'})}


def _build_browser_data(information_override=None):
    from .published_catalog_information import published_information, apply_published_information
    information=published_information() if information_override is None else information_override
    resolved_root=CATALOG_TB_ROOT.resolve()
    html=(CATALOG_TB_ROOT/'index.html').read_text(encoding='utf-8')
    match=re.search(r'<script id="catalog-data" type="application/json">(.*?)</script>',html,re.S)
    if not match:raise ValueError('CatalogTB index data is missing')
    source=json.loads(match[1]);profiles=[]
    # The HTML supplies display hints, never the inventory authority.
    known={unquote(p['json']):p for p in source['profiles'] if p.get('json')}
    known_ids={p.get('id'):p for p in source['profiles']}
    originals=[]
    for path in sorted(CATALOG_TB_ROOT.rglob('thong_tin_thiet_bi.json')):
        relative=path.relative_to(CATALOG_TB_ROOT).as_posix()
        current=json.loads(path.read_text(encoding='utf-8-sig'))
        current=apply_published_information(current,relative,information)
        if current.get('browser_hidden'):continue
        profile_id='TB-'+hashlib.sha1(relative.encode()).hexdigest()[:16]
        original=dict(known.get(relative) or known_ids.get(profile_id) or {})
        original.update(json=relative)
        original['_current_profile']=current
        original.setdefault('display',current.get('ten_san_pham') or path.parent.name)
        original.setdefault('category',current.get('nhom') or 'Thiết bị')
        original.setdefault('brand',current.get('hang_xac_nhan'))
        views=[]
        for view in current.get('cad_don',[]):
            drawing=(path.parent/view.get('duong_dan','')).resolve()
            if not drawing.is_relative_to(resolved_root) or not drawing.is_file():continue
            views.append({'source_id':view['id_hinh_goc'],'face':view.get('huong_nhin','Mặt trước'),
                          'label':view.get('nhan_hien_thi') or view.get('huong_nhin','Mặt trước')})
        if not views:continue
        original['single_views']=views
        preferred=(current.get('cad_chen_tu') or {}).get('id_hinh_goc')
        original['primary']={'source_id':next((v['source_id'] for v in views if v['source_id']==preferred),views[0]['source_id'])}
        originals.append(original)
    for original in originals:
        relative=unquote(original['json'])
        path=(CATALOG_TB_ROOT/relative).resolve()
        if not path.is_relative_to(resolved_root) or path.name!='thong_tin_thiet_bi.json':continue
        cid='TB-'+hashlib.sha1(path.relative_to(CATALOG_TB_ROOT).as_posix().encode()).hexdigest()[:16]
        profile={k:v for k,v in original.items() if k not in {'json','drawings','single_views','primary','sources','_current_profile','catalog_information','visual_candidates'}}
        profile['id']=cid
        current=original['_current_profile']
        if current.get('nhom_thu_vien'):
            profile['category']=current['nhom_thu_vien']
        profile['catalog_references']=current.get('catalog_tham_khao') or {}
        profile['display']=current.get('ten_san_pham') or profile.get('display')
        profile['spec']={**(profile.get('spec') or {}),**(current.get('thong_so') or {})}
        # Old embedded snapshots cannot restore an identity cleared in the source.
        # Reviewed model evidence is applied below after checking its hashes.
        profile['product_code']=current.get('ma_dong_san_pham')
        profile['use']=current.get('cong_dung') or profile.get('use')
        profile['source_catalog_review']=current.get('source_catalog_review') or {}
        identification=current.get('nhan_dien_web') or {}
        if identification.get('user_accepts_approximate_family'):
            profile['display']=current.get('ten_san_pham') or profile['display']
            profile['use']=current.get('cong_dung') or profile.get('use')
        # The embedded HTML may contain aliases from older catalog enrichment.
        # Current source aliases are authoritative; selectable model references
        # are searched separately so removed/incorrect aliases cannot return.
        profile['search_aliases']=list(dict.fromkeys(current.get('tu_khoa_tim_kiem') or []))
        profile['brand']=current.get('hang_xac_nhan') or identification.get('brand_candidate') or profile.get('brand')
        profile['brand_identification_status']='verified' if current.get('hang_xac_nhan') else identification.get('status','unknown')
        ai=current.get('nhan_dien_ai') or {}
        profile['ai_identification']=ai
        profile['recognition_review']=current.get('nhan_dien_bo_sung_20261010') or {}
        profile['auto_select']=bool(current.get('auto_select',False))
        profile['needs_review']=current.get('needs_review',True)
        kind=current.get('catalog_information_type') or ai.get('loai_thiet_bi_code') or profile['recognition_review'].get('category_code')
        if kind:profile['type']={'PHASE_RELAY':'Rơ le bảo vệ pha'}.get(kind,kind)
        profile['views']=[{'id':v['source_id'],'label':v.get('label') or v['face'],'face':v['face'],
                           'preview':f'/equipment-library/{cid}/views/{quote(v["source_id"],safe="")}/preview',
                           'download':f'/equipment-library/{cid}/views/{quote(v["source_id"],safe="")}/dxf'}
                          for v in original['single_views']]
        profile['primary_view']=original['primary']['source_id']
        current_views={v['id_hinh_goc']:v for v in current.get('cad_don',[])}
        for view in profile['views']:
            latest=current_views.get(view['id']) or {}
            if latest.get('huong_nhin'):view['face']=latest['huong_nhin']
            if latest.get('kiem_tra_net_cad'):view['linework_review']=latest['kiem_tra_net_cad']
            preview_file=path.parent/Path(latest.get('duong_dan','')).parent/'xem_truoc.svg'
            if preview_file.is_file():
                stat=preview_file.stat()
                # Cache busting needs a file revision, not a full SVG content scan.
                revision=f'{stat.st_mtime_ns}:{stat.st_size}'
                view['preview']+='?revision='+hashlib.sha256(revision.encode()).hexdigest()[:16]
            if (latest.get('nhan_dien_mat') or {}).get('method')=='individual_visual_review':
                view['label']=latest['huong_nhin']
            elif profile['recognition_review'].get('face'):view['label']=profile['recognition_review']['face']
        for view in profile['views']:
            metadata_path=path.parent/'HinhChieu'/view['id']/'thong_tin.json'
            if metadata_path.is_file():
                metadata=json.loads(metadata_path.read_text(encoding='utf-8'))
                attributes=metadata.get('source_attributes',{})
                view['source_info']={label:attributes[key] for key,label in [('ORIGIN','Hãng'),('TYPE','Mã trên CAD'),('POLES','Số cực / mặt'),('RATE','Dòng ghi trên CAD')] if attributes.get(key)}
        # Show the complete supplier reference first where a source connection
        # assembly has been restored. Other variants remain selectable.
        complete=next((v for v in profile['views'] if v['id'].startswith('LS-ORIGINAL-')),None)
        if complete:profile['primary_view']=complete['id']
        for view in profile['views']:
            if 'COVER' in view['id'].upper():
                view['label']='Nắp che mặt trước'
        counts={label:sum(v['label']==label for v in profile['views']) for label in {v['label'] for v in profile['views']}}
        seen={}
        for view in profile['views']:
            label=view['label'];seen[label]=seen.get(label,0)+1
            if counts[label]>1:view['label']=f'{label} · bản {seen[label]}'
        from .library_manufacturer_identity import manufacturer_identity
        profile.update(manufacturer_identity(profile, current, path))
        reviewed = profile.get('reviewed_description') or {}
        for key in ('display', 'type', 'use', 'product_code', 'manufacturer_document'):
            if reviewed.get(key):
                profile[key] = reviewed[key]
        if reviewed.get('source_model_reference'):
            profile['spec'] = {**profile.get('spec', {}), **reviewed.get('reviewed_spec', {})}
            profile['auto_select'] = False
            profile['needs_review'] = True
        for view in profile['views']:
            label=(reviewed.get('reviewed_view_labels') or {}).get(view['id'])
            if label:
                view['label']=label
                view['face']=label
        from .library_control_meter_review import apply_review
        apply_review(profile, current, path)
        from .catalog_source_identification import apply_source_identification
        apply_source_identification(profile,current,path,CATALOG_TB_ROOT)
        profiles.append(profile)
    from .catalog_projection_corrections import apply_projection_corrections
    apply_projection_corrections(profiles,CATALOG_TB_ROOT)
    groups_path=CATALOG_TB_ROOT/'ai_device_groups.json'
    registry=json.loads(groups_path.read_text(encoding='utf8')) if groups_path.is_file() else {}
    for group in registry.get('groups',[]):
        member_ids={'TB-'+hashlib.sha1(m['profile'].encode()).hexdigest()[:16] for m in group['profiles']}
        members=[p for p in profiles if p['id'] in member_ids]
        if len(members)!=len(member_ids):raise ValueError('Reviewed CAD group has missing profiles')
        merged=dict(members[0]);merged['id']=group['id'];merged['display']=group['name'];merged['type']=group['category']
        merged['views']=[v for member in members for v in member['views']]
        merged['primary_view']=next((v['id'] for v in merged['views'] if v['face']=='Mặt trước'),merged['views'][0]['id'])
        merged['physical_family_id']=group['id'];merged['member_profile_ids']=sorted(member_ids)
        references={}
        for member in members:
            for option in (member.get('catalog_references') or {}).get('options', []):
                references.setdefault((option['brand'],option['model']),option)
        merged['catalog_references']={**(merged.get('catalog_references') or {}),'options':list(references.values())}
        merged['auto_select']=False;merged['needs_review']=True
        profiles=[p for p in profiles if p['id'] not in member_ids]+[merged]
    from .catalog_visual_candidates import apply_visual_candidates
    apply_visual_candidates(profiles,CATALOG_TB_ROOT)
    from .library_ordering_configurations import ordering_configurations
    from .library_catalog_references import catalog_reference
    for profile in profiles:
        profile['ordering_configurations']=ordering_configurations(profile)
        profile['catalog_reference']=catalog_reference(profile)
    categories=[{'name':name,'count':sum(p['category']==name for p in profiles)} for name in sorted({p['category'] for p in profiles})]
    labels={}
    for block in re.findall(r'const (?:extraLabels|labels)=\{([^}]+)\}',html):
        for key,literal in re.findall(r'(\w+)\s*:\s*(\'(?:\\.|[^\'\\])*\'|"(?:\\.|[^"\\])*")',block):
            labels[key]=ast.literal_eval(literal)
    return {'items':profiles,'categories':[c for c in categories if c['count']], 'labels':labels,
            'total':len(profiles),'view_count':sum(len(p['views']) for p in profiles)}

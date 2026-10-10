"""Public display metadata from CatalogTB only, without filesystem paths."""
import ast,hashlib,json,re
from pathlib import Path
from urllib.parse import unquote,quote
from .equipment_library import CATALOG_TB_ROOT

def browser_data():
    html=(CATALOG_TB_ROOT/'index.html').read_text(encoding='utf-8')
    match=re.search(r'<script id="catalog-data" type="application/json">(.*?)</script>',html,re.S)
    if not match:raise ValueError('CatalogTB index data is missing')
    source=json.loads(match[1]);profiles=[]
    for original in source['profiles']:
        relative=unquote(original['json'])
        path=(CATALOG_TB_ROOT/relative).resolve()
        if not path.is_relative_to(CATALOG_TB_ROOT.resolve()) or path.name!='thong_tin_thiet_bi.json':continue
        cid='TB-'+hashlib.sha1(path.relative_to(CATALOG_TB_ROOT).as_posix().encode()).hexdigest()[:16]
        profile={k:v for k,v in original.items() if k not in {'json','drawings','single_views','primary','sources'}}
        profile['id']=cid
        current=json.loads(path.read_text(encoding='utf-8'))
        ai=current.get('nhan_dien_ai') or {}
        profile['ai_identification']=ai
        profile['recognition_review']=current.get('nhan_dien_bo_sung_20261010') or {}
        profile['auto_select']=bool(current.get('auto_select',False))
        profile['needs_review']=current.get('needs_review',True)
        kind=ai.get('loai_thiet_bi_code') or profile['recognition_review'].get('category_code')
        if kind:profile['type']=kind
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
            if preview_file.is_file():view['preview']+='?revision='+hashlib.sha256(preview_file.read_bytes()).hexdigest()[:16]
            if profile['recognition_review'].get('face'):view['label']=profile['recognition_review']['face']
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
        profiles.append(profile)
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
        merged['auto_select']=False;merged['needs_review']=True
        profiles=[p for p in profiles if p['id'] not in member_ids]+[merged]
    categories=[{'name':c['name'],'count':sum(p['category']==c['name'] for p in profiles)} for c in source['categories']]
    labels={}
    for block in re.findall(r'const (?:extraLabels|labels)=\{([^}]+)\}',html):
        for key,literal in re.findall(r'(\w+)\s*:\s*(\'(?:\\.|[^\'\\])*\'|"(?:\\.|[^"\\])*")',block):
            labels[key]=ast.literal_eval(literal)
    return {'items':profiles,'categories':[c for c in categories if c['count']], 'labels':labels,
            'total':len(profiles),'view_count':sum(len(p['views']) for p in profiles)}

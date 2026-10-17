"""Ship opaque catalog keys and product facts; keep extraction provenance private."""
import hashlib
import json
from pathlib import Path
from app.services.customer_equipment_information import customer_device,external_url,INTERNAL
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'app/data'


def cid(value):return value if value.startswith('TB-') else 'TB-'+hashlib.sha1(value.encode()).hexdigest()[:16]
def vid(value):return value if value.startswith('v-') else 'v-'+hashlib.sha256(value.encode()).hexdigest()[:20]
def save(name,data):
    if name=='catalogtb_published_information.json':
        payload='{"schema_version":2,"prices":"---","profiles":{\n'+',\n'.join(json.dumps(k)+':'+json.dumps(v,ensure_ascii=False,separators=(',',':')) for k,v in data['profiles'].items())+'\n}}\n'
    else:payload=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    (DATA/name).write_text(payload,encoding='utf8')


def main(private_information=None):
    # The private original is retained locally; the tracked overlay contains no
    # filesystem paths, drawing block names, extraction pages or review notes.
    from app.services.catalogtb_browser import _build_browser_data
    snapshot=_build_browser_data(information_override=private_information)
    devices={mid:item for item in snapshot['items'] for mid in item.get('member_profile_ids') or [item['id']]}
    current={'profiles':private_information} if private_information is not None else json.loads((DATA/'catalogtb_published_information.json').read_text(encoding='utf8'))
    profiles={}
    for relative,row in current['profiles'].items():
        key=cid(relative);device=devices.get(key)
        if not device:continue
        public=customer_device(device)
        reference={'category':(row.get('catalog_tham_khao') or {}).get('category'),'options':public['catalog_references']['options']}
        for option in reference['options']:option['price']='---'
        profiles[key]={'ten_san_pham':public['display'],'catalog_tham_khao':reference,
            **{k:row[k] for k in ('catalog_information_type','nhom_thu_vien') if k in row}}
    # Group membership can contain multiple raw records; preserve every key in
    # the reviewed overlay even when the public card is grouped.
    save('catalogtb_published_information.json',{'schema_version':2,'prices':'---','profiles':profiles})
    identities=json.loads((DATA/'catalog_source_identification.json').read_text(encoding='utf8'))
    published={}
    for relative,record in identities['profiles'].items():
        out={k:record[k] for k in ('status','checked_at','source_fingerprint','contains_multiple_components','ordering_code_verified','geometry_verified') if k in record}
        out['views']=[{'id':vid(v['id']),'sha256':v['sha256']} for v in record['views']]
        out['source_models_read']=[m for m in record.get('source_models_read',[]) if not m.startswith('*') and not INTERNAL.search(m)]
        out['documented_models']=[]
        for model in record.get('documented_models',[]):
            docs=[{k:d.get(k) for k in ('url','page','sha256','format','match','basis')} for d in model['documents'] if external_url(d.get('url'))]
            if docs:out['documented_models'].append({**model,'documents':docs})
        published[cid(relative)]=out
    save('published_catalog_identification.json',{'schema_version':1,'profiles':published})
    visual=json.loads((DATA/'catalog_visual_candidates.json').read_text(encoding='utf8'))
    visual_out={}
    for relative,records in visual['profiles'].items():
        result=[]
        for record in records:
            out=dict(record);out['source_view']=vid(out['source_view']);out['candidate_view']=vid(out['candidate_view']);out['candidate_profile']=cid(out['candidate_profile'])
            result.append(out)
        visual_out[cid(relative)]=result
    save('published_visual_candidates.json',{'schema_version':1,'profiles':visual_out})
    corrections=json.loads((DATA/'catalog_projection_corrections.json').read_text(encoding='utf8'))
    for row in corrections['items']:
        row['profile']=cid(row['profile']);row['view']=vid(row['view'])
        if row.get('target_profile'):row['target_profile']=cid(row['target_profile'])
    save('published_projection_corrections.json',corrections)
    print('Published opaque customer catalog records:',len(profiles),flush=True)


if __name__=='__main__':main()

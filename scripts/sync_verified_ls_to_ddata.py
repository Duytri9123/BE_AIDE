"""Record visually checked LS price/CAD links back into D:\\data."""
import json
import shutil
from pathlib import Path

root=Path(__file__).resolve().parents[2]
source=root/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/LS_D02_DU_LIEU_MOI'
native=source/'native'
data=Path(r'D:\data')
folder=data/'catalog_sources/ls_2026-10-01'
export=folder/'verified_cad'
export.mkdir(exist_ok=True)
rows=json.loads((source/'price_with_cad.json').read_text(encoding='utf8'))
by_id={row['row_id']:row for row in rows}
row_ids=(29,30,32,33,50,51,53,54,161,170,171,172,173,174,175,176,177)
stems=sorted({by_id[row_id]['cad_device_id'] for row_id in row_ids})
for stem in stems:
    for suffix in ('.dwg','.dxf','-verified.png','-source.json'):
        src=native/(stem+suffix)
        assert src.is_file(),src
        dst=export/src.name
        shutil.copy2(src,dst)

matches=[]
for row_id in row_ids:
    row=by_id[row_id]
    stem=row['cad_device_id']
    matches.append({
        'ls_price_row_id':row_id,'model_pdf':row['model'],
        'name_pdf':row['name_pdf'],'poles_pdf':row['poles_pdf'],
        'price_vnd_ex_vat':row['price_vnd_ex_vat'],
        'cad_match_level':row['cad_match_level'],
        'cad_match_basis':row['cad_match_basis'],
        'cad_evidence_url':row.get('cad_evidence_url'),
        'cad_connection_points':row.get('cad_connection_points'),
        'cad_dwg':f'verified_cad/{stem}.dwg',
        'cad_dxf':f'verified_cad/{stem}.dxf',
        'cad_preview':f'verified_cad/{stem}-verified.png',
        'cad_provenance':f'verified_cad/{stem}-source.json',
        'manufacturer_and_trip_note':'CAD theo họ/khung; mã dòng cắt N/H hoặc điện áp cuộn hút không được xác nhận từ hình'
    })
manifest={'source_price_pdf':'Bang-gia-LS-2026-10-01.pdf',
          'price_effective_date':'2026-10-01',
          'source_library_dwg':'LS-device-library.dwg',
          'additional_original_dwg':'E:/duytristool/AIDE_website/Tudien/THƯ VIỆN PHỤ KIỆN( Mới nhất).dwg',
          'manufacturer_dimension_source':'https://www.ls-electric.com/upload/customer/download/1573/1600AF_Susol%20MCCB.pdf',
          'match_method':'Read original blocks and inspect rendered CAD, terminal count and internal model text; check shared TS1600AF housing with the LS technical table; no added geometry.',
          'matched_price_rows':matches,
          'still_unmatched_examples':['LA63N 1P/2P/3P/4P','LA63H 1P/2P/3P/4P'],
          'limitation':'Unmatched rows are not assigned a similar-looking device merely from JSON name or dimensions.'}
(folder/'verified_price_cad_matches.json').write_text(
    json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
source_record=folder/'source.json'
source_info=json.loads(source_record.read_text(encoding='utf8'))
source_info['verified_cad_manifest']='verified_price_cad_matches.json'
source_info['verified_cad_assets_directory']='verified_cad'
source_record.write_text(json.dumps(source_info,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

# The existing product record and CAD asset already live under D:\data. Link
# them with an explicit frame/coil limitation; do not change product specs.
sku=data/'thu_vien_tu_dien_v2/san_pham/LS/MC/MC-32A__sku_19e6299ee38e029e.json'
item=json.loads(sku.read_text(encoding='utf8'))
assert item['sku'].upper()=='MC-32A' and item['specifications']['p']==3
asset=data/'thu_vien_tu_dien_v2/thiet_bi/contactor/LS/MC_32AF__lib_1a830b1042ae146bb245'
for name in ('cad.dxf','preview.svg','ban_ve_nguon.dxf'):
    assert (asset/name).is_file(),name
link={'asset_id':'lib_1a830b1042ae146bb245',
      'cad':'thiet_bi/contactor/LS/MC_32AF__lib_1a830b1042ae146bb245/ban_ve_nguon.dxf',
      'preview':'thiet_bi/contactor/LS/MC_32AF__lib_1a830b1042ae146bb245/preview.svg',
      'status':'visually_checked_shared_frame',
      'evidence':{'source_text':['LS','MC 32AF/3P Series'],
                  'source_poles':3,'catalog_poles':3,
                  'source_file':'@LS_recover.dwg',
                  'price_row_id':161,
                  'coil_voltage_on_cad':None},
      'approved_for_manufacture':False}
if not any(x.get('asset_id')==link['asset_id'] for x in item['cad_links']):
    item['cad_links'].append(link)
item['cad_status']='has_reference_drawing'
sku.write_text(json.dumps(item,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
missing_queue=data/'thu_vien_tu_dien_v2/cho_doi_chieu/sku_chua_co_cad.json'
queue=json.loads(missing_queue.read_text(encoding='utf8'))
queue=[entry for entry in queue if entry.get('id')!=item['id']]
missing_queue.write_text(json.dumps(queue,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'verified_cad_assets':len(stems),
                  'price_rows':len(matches),'updated_product':str(sku),
                  'remaining_missing_cad_products':len(queue)},ensure_ascii=True))

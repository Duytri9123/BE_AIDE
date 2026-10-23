"""Reviewed source additions after the whole-library orientation audit."""
import json,hashlib
from ls_native_writer import ROOT,CAT,write_profile,price_option,REPORT
from import_ls_step_family import entities
from import_chint_reviewed_step_faces import NXM250

FLIPPED=[('FRONT','FRONT',180),('REAR','REAR',180),('SIDE-L','SIDE',180),('SIDE','SIDE-L',180),('TOP','BOTTOM',180),('BOTTOM','TOP',180)]

def source_for(brand,ident,mapping):
 p=CAT/brand/'NguonBenNgoai'/ident;source=json.loads((p/'source.json').read_text())
 source.update(step_sha256=hashlib.sha256((p/'source.step').read_bytes()).hexdigest(),projection_method='Open CASCADE polygonal visible-edge HLR; absolute mesh deflection 0.05 mm',unit_evidence='Manufacturer STEP; imported in MM; DXF INSUNITS=4',axis_mapping=[{'view':c,'source_projector':o,'rotation_degrees':a} for c,o,a in mapping],six_views_verified=True)
 return source

def main():
 ls_families=[]
 for ident,poles in [('55731/model-030','3P'),('55731/model-031','4P')]:
  views,_=entities(ident,FLIPPED);assert views
  source=source_for('LS',ident,FLIPPED);source['family_compatibility_evidence']={'catalogue':'METASOL-MS-CATALOG-202609/source.pdf','pdf_page':93,'review':'AR-600 source contains two contactors plus the interlock/baseplate. Retain complete assembly; do not link the whole assembly to the standalone AR-600 price. Front is rotated upright using the terminal/coil markings; other five projections use the same physical frame.'}
  family='STEP-'+ident.replace('/','-');p=write_profile(family,'LS · Cụm đảo chiều AR-600 · '+poles,'ASSEMBLY_REFERENCE',['AR-600'],poles,[],views,source,{'Phạm vi CAD':'Cụm gồm 2 contactor, bộ liên động và đế gá','Số cực tham chiếu':poles+' của mỗi contactor','Đặt hàng':'Chọn riêng mã contactor, cuộn hút và bộ liên động; không coi giá AR-600 là giá toàn cụm'})
  d=json.loads(p.read_text(encoding='utf8'));d['cau_truc_cum']={'physical_units_per_cad':2,'includes':'two contactors, mechanical interlock and baseplate','single_device_price_applicable':False};p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');ls_families.append(family)
 ident='NXM-250S-4P-v1';views,_=entities(ident,NXM250,'Chint');assert views
 from ezdxf import bbox
 b=bbox.extents(views[0][2]).size;assert abs(b.x-140)<.2 and abs(b.y-165)<.2
 rows=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'];rows=[r for r in rows if str(r.get('brand')).upper()=='CHINT' and r.get('category')=='MCCB' and r['sku'].startswith('NXM-250S/4')];assert rows
 source=source_for('Chint',ident,NXM250);alias=json.loads((CAT/'Chint/NguonBenNgoai/NXM-250S-4P-v2/source.json').read_text());assert alias['sha256']==source['sha256'];source['identical_source_aliases']=[alias['source_url']]
 source['family_compatibility_evidence']={'catalogue':'NXM-CATALOG/source.pdf','pdf_pages':[9,27],'front_width_mm':140,'front_height_mm':165,'review':'Manufacturer NXM-250S 4-pole source. Terminal N is visible on the front. Neutral A/B/C/D mechanism and release must be verified by ordering code. Two official download links have identical SHA256; imported once. Full depth includes original handle pose.'}
 ch_family='STEP-'+ident;write_profile(ch_family,'MCCB CHINT NXM-250S · 4P · 180–250 A · Icu 36 kA','MCCB',['NXM-250S'],'4P',[price_option(r,brand='CHINT') for r in rows],views,source,{'so_cuc':'4P','Kiểu lắp':'Cố định; đầu nối phía trước','Cực N':'Kiểm tra cơ cấu trung tính theo mã đặt hàng','Bao hình':'Bao gồm tư thế tay gạt của mô hình chính hãng'},brand='CHINT')
 for brand,report,families in [('LS',REPORT,ls_families),('CHINT',ROOT/'docs/chint-full-faces-2026-10-21.json',[ch_family])]:
  rows=[r for r in json.loads(report.read_text()) if r['family'] in families]
  (ROOT/('docs/ls-chint-review-additions-'+brand+'.json')).write_text(json.dumps(rows,indent=2),encoding='utf8')
 print('Added 2 LS assembly families and 1 CHINT individual device family')
if __name__=='__main__':main()

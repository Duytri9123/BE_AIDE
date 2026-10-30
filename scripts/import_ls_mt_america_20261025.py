"""Import individually reviewed MT STEP configurations from LS America."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from import_ls_step_family import import_family, PRICES, CAT, ROOT
from ls_native_writer import price_option

# Source projection FRONT is an arbitrary projector label, not a device face.
FORWARD=[('FRONT','FRONT',90),('REAR','REAR',-90),
         ('SIDE-L','TOP',90),('SIDE','BOTTOM',90),
         ('TOP','SIDE',90),('BOTTOM','SIDE-L',90)]
BACKWARD=[('FRONT','FRONT',-90),('REAR','REAR',90),
          ('SIDE-L','BOTTOM',-90),('SIDE','TOP',-90),
          ('TOP','SIDE-L',-90),('BOTTOM','SIDE',-90)]
LARGE400=[('FRONT','REAR',-90),('REAR','FRONT',90),
          ('SIDE-L','BOTTOM',-90),('SIDE','TOP',-90),
          ('TOP','SIDE',-90),('BOTTOM','SIDE-L',-90)]
LARGE800=[('FRONT','BOTTOM',-90),('REAR','TOP',90),
          ('SIDE-L','REAR',90),('SIDE','FRONT',-90),
          ('TOP','SIDE-L',0),('BOTTOM','SIDE',0)]
JOBS=[('33168','MT-12',FORWARD,'Pin',171),
      ('33169','MT-32',BACKWARD,'Pin',171),
      ('25306','MT-63',BACKWARD,'Screw',171),
      ('22403','MT-95',BACKWARD,'Screw',171),
      ('33178','MT-150',BACKWARD,'Screw',172),
      ('23731','MT-225',BACKWARD,'Lug',172),
      ('33175','MT-400',LARGE400,'Lug',172),
      ('22404','MT-800',LARGE800,'Panel assembly',172)]
OUT=ROOT/'docs/ls-all-cad-2026-10-24'

def main():
    reports=[]
    for ident, model, mapping, terminal, page in JOBS:
        choose=lambda r,m=model:r.get('category')=='THERMAL_RELAY' and r['sku'].split()[0]==m
        path=import_family('AMERICA-'+ident,'THERMAL_RELAY',[model],None,choose,
            mapping=mapping,family='AMERICA-'+model+'-'+terminal.split()[0].upper(),
            name='LS · Rơ le nhiệt · '+model+' · '+terminal,
            spec={'Kiểu đầu nối theo CAD':terminal,'Tiếp điểm phụ':'1NO + 1NC',
                  'Phạm vi xác minh':'CAD họ theo cấu hình đầu nối; chưa xác nhận mã đặt hàng, số heater hoặc cấp tác động'},
            evidence={'catalog_url':'https://www.ls-electric.com/upload/customer/download/280b6197-f4bb-4f86-a60d-917b7b8bf890/Metasol_MC_E_170915.pdf',
                      'pdf_pages':[page,95],
                      'orientation_review':'Front is the adjustment dial and NC/NO/main terminal face. Main incoming pins/lugs above outgoing screws. MT800 front is the relay on the lower part of the vertical panel. Rear is the opposite mounting face.',
                      'configuration_scope':'Source filename establishes frame and terminal variant; family price reference only, no exact ordering SKU approval. STEP geometry retained without stretching to older catalog dimensions.'})
        assert path
        reports.append({'model':model,'profile':path.relative_to(CAT).as_posix(),
                        'source':'LS/NguonBenNgoai/AMERICA-'+ident,
                        'views':6,'price_ids':[r['id'] for r in PRICES if choose(r)],
                        'terminal':terminal,'catalog_pdf_page':page})
    (OUT/'mt-america-additions-20261025.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf8')
    return reports

if __name__=='__main__': main()

"""Attach the explicit 4-pole specification of four reviewed Metasol models."""
import json
from pathlib import Path

SOURCE='https://www.ls-electric.com/upload/customer/download/280b6197-f4bb-4f86-a60d-917b7b8bf890/Metasol_MC_E_170915.pdf'
MODELS={'MC-6a/4','MC-9a/4','MC-12a/4','MC-18a/4'}


def review(rows):
    count=0
    for row in rows:
        if row.get('brand') != 'LS Electric' or row.get('category') != 'CONTACTOR' or row.get('sku') not in MODELS:
            continue
        row.setdefault('specifications',{})['Số cực']='4P'
        row['specification_review']={'source_url':SOURCE,'source_page_label':'14','checked_date':'2026-10-14',
                                     'note':'Number of poles: 4pole; exact MC-6a/4, MC-9a/4, MC-12a/4, MC-18a/4 model table. Not a coil-voltage or CAD geometry approval.'}
        count+=1
    return count


if __name__ == '__main__':
    path=Path(__file__).resolve().parents[1]/'app/data/supplier_pricebooks.json'
    data=json.loads(path.read_text(encoding='utf8'))
    print('Reviewed rows',review(data['items']))
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

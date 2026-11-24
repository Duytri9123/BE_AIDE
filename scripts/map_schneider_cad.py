import sqlite3
import json

db_path = r'E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\_agent_index\equipment_catalog.sqlite'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT catalog_id, brand, model, category, record_json FROM equipment WHERE brand LIKE '%schneider%'")
records = []
for r in cur.fetchall():
    rec = json.loads(r[4])
    dir_name = rec.get('cad', {}).get('preview', {}).get('path', '')
    records.append({
        'catalog_id': r[0],
        'model': r[2],
        'category': r[3],
        'dir': dir_name,
        'poles': rec.get('specifications', {}).get('Số cực') or rec.get('thong_so', {}).get('so_cuc')
    })

print(f"Total Schneider equipment in sqlite: {len(records)}")
# Print distinct models & dirs
by_model = {}
for r in records:
    m = r['model']
    by_model.setdefault(m, []).append(r)

for m, recs in sorted(by_model.items()):
    dirs = [x['dir'].split('/')[3] if len(x['dir'].split('/')) > 3 else x['dir'] for x in recs]
    print(f"  Model: {m} -> {len(recs)} items (dirs: {set(dirs)})")

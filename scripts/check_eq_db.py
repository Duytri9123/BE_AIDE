import sqlite3
import json

db_path = r'E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\_agent_index\equipment_catalog.sqlite'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM equipment WHERE brand LIKE '%schneider%'")
print('Total Schneider equipment records:', cur.fetchone()[0])

cur.execute("SELECT catalog_id, brand, model, category, record_json FROM equipment WHERE brand LIKE '%schneider%' LIMIT 10")
for r in cur.fetchall():
    rec = json.loads(r[4])
    cad = rec.get('cad', {})
    print(f"catalog_id={r[0]} | model={r[2]} | preview={cad.get('preview', {}).get('path')}")

"""Return complete catalog records for an AI consumer or a command-line user."""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / 'Tudien/CATALOG_PHU_KIEN_DOC_LAP/THU_VIEN_THIET_BI_AI_2026/equipment_catalog.sqlite'


def main():
    parser = argparse.ArgumentParser(description='Search the unified AIDE equipment catalog')
    parser.add_argument('text', nargs='?', help='Model, device name, or category')
    parser.add_argument('--brand', help='Exact brand label, e.g. LS or Mitsubishi')
    parser.add_argument('--cad', choices=('any', 'available', 'exact', 'none'), default='any')
    parser.add_argument('--limit', type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.limit <= 500:
        parser.error('--limit must be between 1 and 500')
    clauses, params = [], []
    words = re.findall(r'\w+', args.text or '', flags=re.UNICODE)
    if words:
        clauses.append('e.catalog_id IN (SELECT catalog_id FROM equipment_fts WHERE equipment_fts MATCH ?)')
        params.append(' AND '.join('"' + word + '"' for word in words))
    if args.brand:
        clauses.append('e.brand = ?')
        params.append(args.brand)
    if args.cad == 'available':
        clauses.append("e.cad_status IN ('exact_model_cad','family_or_frame_cad','source_cad_family','source_cad_unverified_sku')")
    elif args.cad == 'exact':
        clauses.append("e.cad_status = 'exact_model_cad'")
    elif args.cad == 'none':
        clauses.append("e.cad_status IN ('no_verified_cad','manufacturer_data_no_cad','manufacturer_dimensions_no_cad')")
    where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
    with sqlite3.connect(DB) as connection:
        rows = connection.execute('SELECT e.record_json FROM equipment e' + where +
                                  ' ORDER BY e.brand,e.model,e.catalog_id LIMIT ?', (*params, args.limit)).fetchall()
    print(json.dumps([json.loads(row[0]) for row in rows], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

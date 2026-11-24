import json
import os

with open("BE_AIDE/app/data/supplier_pricebooks.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"type(data): {type(data)}")
if isinstance(data, dict):
    print(f"data keys: {list(data.keys())[:15]}")
    sample_key = list(data.keys())[0]
    print(f"sample key '{sample_key}': type={type(data[sample_key])}")
    print(f"sample content: {data[sample_key] if not isinstance(data[sample_key], list) else f'list of len {len(data[sample_key])}, item 0: {data[sample_key][0]}'}")

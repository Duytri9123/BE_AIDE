"""Build a lightweight, deterministic index for a DXF/DWG device library."""
from __future__ import annotations

import argparse
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import ezdxf
from ezdxf import bbox


def compact(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def tokens(value: Any) -> set[str]:
    return {v.lower() for v in re.findall(r"[A-Za-z]+|\d+", str(value or "")) if len(v) > 1}


def useful(name: str, vocabulary: set[str]) -> bool:
    key = compact(name)
    if not key or name.startswith("*") or name.upper().startswith("A$C"):
        return False
    return bool(tokens(name) & vocabulary)


def extent(layout) -> dict[str, float] | None:
    try:
        box = bbox.extents(layout, fast=True)
        if not box.has_data:
            return None
        return {
            "min_x": round(box.extmin.x, 4), "min_y": round(box.extmin.y, 4),
            "max_x": round(box.extmax.x, 4), "max_y": round(box.extmax.y, 4),
            "width": round(box.size.x, 4), "height": round(box.size.y, 4),
        }
    except Exception:
        return None


def score(item: dict[str, Any], block: dict[str, Any]) -> float:
    model = str(item.get("manufacturer_sku") or item.get("ma") or "")
    name = block["name"]
    model_tokens, block_tokens = tokens(model), tokens(name)
    shared = model_tokens & block_tokens
    value = SequenceMatcher(None, compact(model), compact(name)).ratio()
    value += 0.22 * len(shared)
    poles = item.get("p")
    if poles and re.search(rf"\b{poles}\s*p\b", name, re.I):
        value += 0.35
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dxf", type=Path)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--library", required=True, help="Portable path stored in the index")
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    source_items = [row for row in catalog if row.get("source", {}).get("id")]
    vocabulary = set().union(*(tokens(row.get("manufacturer_sku")) for row in source_items))
    vocabulary |= {compact(row.get("brand_display")) for row in source_items}

    doc = ezdxf.readfile(args.dxf)
    blocks = []
    for layout in doc.blocks:
        if useful(layout.name, vocabulary):
            blocks.append({
                "name": layout.name,
                "entity_count": len(layout),
                "bounds": extent(layout),
            })

    mapped = 0
    for item in source_items:
        ranked = sorted(((score(item, block), block) for block in blocks), key=lambda pair: pair[0], reverse=True)
        best_score, best = ranked[0] if ranked else (0.0, None)
        selector = {
            "library_id": args.output.stem,
            "category": item.get("t"), "poles": item.get("p"), "rated_current_a": item.get("in"),
            "strategy": "exact_name_then_smallest_compatible_frame",
        }
        # A low-confidence fuzzy result remains a selector hint, never an exact block.
        if best and best_score >= 0.92:
            selector.update({"block": best["name"], "match_score": round(best_score, 3)})
            mapped += 1
        item["cad"] = selector

    payload = {
        "format_version": 1,
        "library_file": args.library,
        "source_dxf_version": doc.dxfversion,
        "units": int(doc.header.get("$INSUNITS", 0)),
        "block_count": len(blocks),
        "blocks": blocks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.catalog.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"indexed_blocks": len(blocks), "exact_or_strong_mappings": mapped, "items": len(source_items)}))


if __name__ == "__main__":
    main()

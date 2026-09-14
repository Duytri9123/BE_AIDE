"""Import a vendor price PDF and optional CAD library into the canonical catalog.

The vendor, effective date and classification rules live in a source manifest;
no manufacturer or SKU list is embedded in this program.  Re-running the
import is idempotent because every price variant receives a deterministic key.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Iterable

import pdfplumber


PRICE_RE = re.compile(r"^\s*[\d.,]+\s*$")
NUMBER_RE = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?")


def compact(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def price_value(value: Any) -> int | None:
    text = str(value or "").strip()
    if not PRICE_RE.match(text):
        return None
    digits = re.sub(r"\D", "", text)
    return int(digits) if digits else None


def rated_values(value: Any) -> list[float]:
    """Expand explicit rating lists but keep adjustment ranges as one variant."""
    text = str(value or "").replace(",", ".")
    prefix = text.split("(", 1)[0]
    numbers = [float(v) for v in NUMBER_RE.findall(prefix)]
    if not numbers:
        return []
    # A parenthesized setting range describes one rated product (MMS/relay).
    if "(" in text or "~" in prefix:
        return [numbers[0]]
    return list(dict.fromkeys(numbers))


def infer_value(title: str, rules: dict[str, Any], default: Any = None) -> Any:
    for value in rules:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(value)}(?![A-Za-z0-9])", title, re.I):
            return value
    normalized = compact(title)
    matches = [
        (len(compact(pattern)), value)
        for value, patterns in rules.items()
        for pattern in patterns
        if compact(pattern) and compact(pattern) in normalized
    ]
    return max(matches)[1] if matches else default


def infer_poles(title: str, model: str) -> int | None:
    text = f"{title} {model}"
    matches = re.findall(r"(?<!\d)([1-4])\s*(?:p|pha|cuc|pole|poles)(?!\w)", text, re.I)
    if matches:
        return int(matches[-1])
    suffix = re.search(r"([234])c\b", model, re.I)
    return int(suffix.group(1)) if suffix else None


def iter_sections(table: list[list[Any]]) -> Iterable[tuple[str, list[Any]]]:
    """Yield (current section title, logical row) from single/side-by-side tables."""
    width = max((len(row) for row in table), default=0)
    group_width = 4 if width >= 8 else width
    groups = max(1, (width + group_width - 1) // group_width)
    titles = ["" for _ in range(groups)]
    for row in table:
        padded = list(row) + [None] * (groups * group_width - len(row))
        for index in range(groups):
            cells = padded[index * group_width:(index + 1) * group_width]
            nonempty = [str(cell).strip() for cell in cells if cell not in (None, "")]
            if not nonempty:
                continue
            if len(nonempty) == 1 and price_value(nonempty[0]) is None:
                titles[index] = nonempty[0]
                continue
            yield titles[index], cells


def parse_pdf(pdf_path: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    source_hash = sha256(pdf_path)
    with pdfplumber.open(pdf_path) as document:
        for page_number, page in enumerate(document.pages, 1):
            for table_number, table in enumerate(page.extract_tables(), 1):
                for title, cells in iter_sections(table):
                    values = [str(cell or "").strip() for cell in cells]
                    if not values or compact(values[0]) in {"tenhang", "model", "sku"}:
                        continue
                    price = next((price_value(v) for v in reversed(values[1:])), None)
                    model = values[0]
                    if price is None or not model or len(model) > 100:
                        continue
                    category = infer_value(title, manifest.get("category_rules", {}), "ACCESSORY")
                    breaker_categories = {"MCCB", "MCB", "ELCB", "RCBO", "RCCB", "ACB", "SPD"}
                    detail_cells = [value for value in values[1:-1] if value]
                    rating = (values[1] if len(values) > 1 else "") if category in breaker_categories else (detail_cells[-1] if detail_cells else "")
                    currents = rated_values(rating) or [None]
                    poles = infer_poles(title, model)
                    breaking = None
                    if category in breaker_categories and len(values) >= 4:
                        nums = rated_values(values[-2])
                        breaking = nums[0] if nums else None
                    for current in currents:
                        pole_label = f"{poles}P" if poles and not re.search(rf"\b{poles}\s*P\b", model, re.I) else ""
                        variant_parts = [model, pole_label, f"{current:g}A" if current is not None else ""]
                        if breaking is not None:
                            variant_parts.append(f"{breaking:g}kA")
                        sku = " ".join(part for part in variant_parts if part)
                        # Configuration is part of identity: ACB fixed/draw-out
                        # or supplied/without accessories may share model/rating.
                        key = "|".join(compact(part) for part in [manifest["manufacturer"], category, sku, title])
                        item = {
                            "ma": sku,
                            "manufacturer_sku": model,
                            "n": f"{model} {rating}".strip(),
                            "brand": manifest["brand_key"],
                            "brand_display": manifest["manufacturer"],
                            "series": re.split(r"[- /]", model, maxsplit=1)[0],
                            "t": category,
                            "p": poles,
                            "in": current,
                            "icu": breaking,
                            "g": price,
                            "catalog_key": key,
                            "configuration": title,
                            "source": {
                                "id": manifest["source_id"], "page": page_number,
                                "table": table_number, "sha256": source_hash,
                                "effective_date": manifest.get("effective_date"),
                                "currency": manifest.get("currency", "VND"),
                                "vat_included": manifest.get("vat_included"),
                            },
                        }
                        items.append({k: v for k, v in item.items() if v is not None})
    # Prefer the last exact variant only if a source itself repeats it.
    return list({item["catalog_key"]: item for item in items}.values())


def load_items(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload.get("items", []) if isinstance(payload, dict) else payload


def merge(existing: list[dict[str, Any]], imported: list[dict[str, Any]], source_id: str) -> list[dict[str, Any]]:
    retained = [item for item in existing if item.get("source", {}).get("id") != source_id]
    # Legacy catalogs may intentionally contain the same SKU in distinct
    # commercial configurations. Preserve them; only this source's stable keys
    # are deduplicated.
    imported_index = {item["catalog_key"]: item for item in imported}
    return sorted(retained + list(imported_index.values()), key=lambda row: (row.get("brand", ""), row.get("t", ""), row.get("ma", "")))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--base", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    pdf_path = (args.manifest.parent / manifest["price_file"]).resolve()
    imported = parse_pdf(pdf_path, manifest)
    existing = load_items(args.catalog) or (load_items(args.base) if args.base else [])
    merged = merge(existing, imported, manifest["source_id"])
    args.catalog.parent.mkdir(parents=True, exist_ok=True)
    if args.catalog.exists():
        shutil.copy2(args.catalog, args.catalog.with_suffix(args.catalog.suffix + ".bak"))
    args.catalog.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"imported": len(imported), "total": len(merged), "catalog": str(args.catalog)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

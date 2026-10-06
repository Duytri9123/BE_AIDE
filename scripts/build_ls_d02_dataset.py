"""Build a traceable, title-free LS D02 CAD dataset from the extracted source views."""
from __future__ import annotations

import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path

import ezdxf
from ezdxf import bbox

ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT / "Tudien/CATALOG_PHU_KIEN_DOC_LAP"
OUT = CAT / "LS_D02_DU_LIEU_MOI"
SOURCE = CAT / "LS_D02_BOC_TACH.html"


def leaf_entities(entity, depth=0):
    if entity.dxftype() != "INSERT" or depth > 10:
        yield entity
        return
    try:
        children = entity.virtual_entities()
        for child in children:
            yield from leaf_entities(child, depth + 1)
    except Exception:
        return


def text_of(entity):
    if entity.dxftype() == "TEXT":
        return entity.dxf.text.strip()
    if entity.dxftype() == "MTEXT":
        return entity.plain_text().strip()
    return ""


def main():
    markup = SOURCE.read_text(encoding="utf-8")
    articles = re.findall(r'<article class="card".*?</article>', markup, re.S)
    records = []
    for article in articles:
        match = re.search(r'LS_D02_HINH_GOC/(D02_cluster(\d+)_item(\d+)\.svg)', article)
        cad_match = re.search(r'href="(04_BO_THIET_BI_DXF/D02/[^"]+\.dxf)" download', article)
        name_match = re.search(r'<h3>(.*?)</h3>', article, re.S)
        block_match = re.search(r'Block gốc: ([^<]+)', article)
        if not (match and cad_match and name_match):
            continue
        cluster, item = int(match.group(2)), int(match.group(3))
        annotated = CAT / cad_match.group(1)
        clean = annotated.with_name(annotated.stem + "_thiet_bi.dxf")
        doc = ezdxf.readfile(clean)
        leaves = [leaf for entity in doc.modelspace() for leaf in leaf_entities(entity)]
        ext = bbox.extents(leaves)
        xmin, ymin = ext.extmin.x, ext.extmin.y
        xmax, ymax = ext.extmax.x, ext.extmax.y
        circles = [e for e in leaves if e.dxftype() == "CIRCLE"]
        texts = sorted({s for e in leaves if (s := text_of(e))})
        label = html.unescape(re.sub(r'<[^>]*>', '', name_match.group(1))).strip()
        detail_match = re.search(r'<details>.*?<summary>.*?</summary>(.*?)</details>', article, re.S)
        source_text = html.unescape(re.sub(r'<[^>]*>', '', detail_match.group(1))).strip() if detail_match else ""
        pole_markers = re.findall(r'(?<!\d)([1-4])P(?:\+N)?', label + ' ' + source_text, re.I)
        poles = int(pole_markers[0]) if pole_markers else None
        # Circles near the upper/lower edges are geometric candidates only.
        height = max(ymax - ymin, 1)
        candidates = []
        for circle in circles:
            x, y = circle.dxf.center.x, circle.dxf.center.y
            edge = "upper" if y >= ymax - .18 * height else "lower" if y <= ymin + .18 * height else None
            if edge:
                candidates.append({"edge": edge, "x_mm": round(x-xmin, 3),
                                   "y_mm": round(y-ymin, 3), "radius_mm": round(circle.dxf.radius, 3),
                                   "role": "geometric_candidate", "phase": None, "terminal_number": None})
        candidates.sort(key=lambda x: (x["edge"], x["x_mm"], x["y_mm"]))
        category = {2: "Contactor / rơle nhiệt", 3: "MCB / RCBO / RCCB",
                    5: "MCCB Susol", 6: "MCCB / ELCB Metasol"}[cluster]
        topology = []
        if poles and cluster in (3, 5, 6):
            for index in range(1, poles + 1):
                topology.append({"pole_index_left_to_right": index,
                                 "upper_port": f"P{index}_upper", "lower_port": f"P{index}_lower",
                                 "phase": None, "terminal_numbers": None,
                                 "status": "logical_pair_only_requires_symbol_and_wiring_review"})
        elif poles == 3 and cluster == 2 and label.startswith('MC '):
            for index in range(1, 4):
                topology.append({"pole_index_left_to_right": index,
                                 "upper_port": f"P{index}_upper", "lower_port": f"P{index}_lower",
                                 "phase": None, "terminal_numbers": None,
                                 "status": "logical_main_contact_only_coil_A1_A2_not_located"})
        record = {
            "id": f"LS-D02-C{cluster}-I{item:02d}", "name": label, "category": category,
            "source_block": block_match.group(1).strip() if block_match else None,
            "source_dwg": "Tudien/THƯ VIỆN PHỤ KIỆN( Mới nhất).dwg",
            "cad_dxf": clean.relative_to(CAT).as_posix(),
            "cad_sha256": hashlib.sha256(clean.read_bytes()).hexdigest(),
            "preview_svg": (Path("LS_D02_HINH_GOC") / match.group(1)).as_posix(),
            "cad_status": "extracted_from_source_dwg_title_removed",
            "entity_types": dict(Counter(e.dxftype() for e in leaves)),
            "size_cad_mm": {"width": round(xmax-xmin, 3), "height": round(ymax-ymin, 3)},
            "cad_units": doc.units,
            "visible_cad_text": texts,
            "source_dwg_annotation_text": source_text.split(' · ') if source_text else [],
            "poles_from_text": poles,
            "connection_points": candidates,
            "connectivity_template": topology,
            "connection_status": "geometric_candidates_unverified",
            "phase_assignment": None,
            "source_load_direction": None,
            "price_match_status": "requires_exact_order_code_and_variant",
        }
        records.append(record)
    OUT.mkdir(exist_ok=True)
    (OUT / "devices.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {"devices": len(records), "by_category": dict(Counter(r["category"] for r in records)),
               "total_geometric_connection_candidates": sum(len(r["connection_points"]) for r in records),
               "source_pdf": "C:/Users/admin/Downloads/Bang gia LS ap dung ngay 01-10-2026.pdf",
               "price_effective_date": "2026-10-01",
               "price_policy": "Do not assign price from frame size or generic CAD. Require exact order code, poles, current, trip and coil variant."}
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()

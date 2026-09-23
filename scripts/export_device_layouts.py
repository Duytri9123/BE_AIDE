"""Export indexed library blocks as independent, millimetre DXF assets."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import ezdxf
from ezdxf import bbox
from ezdxf.addons import Importer


def block_brand(name, source_brand):
    key = name.upper()
    for marker, label in (("HYUNDAI", "Hyundai"), ("LS ", "LS"), ("CHINT", "Chint"), ("SCHNEIDER", "Schneider Electric")):
        if marker in key:
            return label
    if re.match(r"^(NX[BM]|NM1|NZ7)", key):
        return "Chint"
    if source_brand == "Schneider Electric" and (" - SC " in key or re.match(r"^(LC1|LV4|NS[X0-9_-]|EZC|CVS|SN_)", key)):
        return source_brand
    return "Chưa xác định hãng"


def export_layouts(source, index_path, output, brand="LS", source_file="@LS_recover.dwg", preserve_units=False):
    doc = ezdxf.readfile(source)
    if doc.units != 4 and not preserve_units:
        raise ValueError("Source units must be confirmed as millimetres before export")
    index = json.loads(Path(index_path).read_text(encoding="utf-8"))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    items, failures = [], []
    for entry in index["blocks"]:
        name = entry["name"]
        asset_id = hashlib.sha256((name if brand == "LS" else source_file + ":" + name).encode()).hexdigest()[:20]
        try:
            target = ezdxf.new("R2018")
            target.units = doc.units
            importer = Importer(doc, target)
            importer.import_block(name)
            importer.finalize()
            insert = target.modelspace().add_blockref(name, (0, 0))
            bounds = bbox.extents(target.modelspace())
            if not bounds.has_data or bounds.size.x <= 0 or bounds.size.y <= 0:
                raise ValueError("Block has no usable 2D bounds")
            insert.translate(-bounds.extmin.x, -bounds.extmin.y, -bounds.extmin.z)
            path = output / f"{asset_id}.dxf"
            target.saveas(path)
            loaded = ezdxf.readfile(path)
            audit = loaded.audit()
            if audit.errors or audit.fixes:
                raise ValueError("DXF audit requires repairs")
            final = bbox.extents(loaded.modelspace())
            if abs(final.extmin.x) > .01 or abs(final.extmin.y) > .01:
                raise ValueError("Origin normalization failed")
            items.append(dict(id=asset_id, name=name, brand=brand if brand == "LS" else block_brand(name, brand), source_brand=brand, filename=path.name,
                              width=round(final.size.x, 3), height=round(final.size.y, 3),
                              width_mm=round(final.size.x, 3) if doc.units == 4 else None,
                              height_mm=round(final.size.y, 3) if doc.units == 4 else None,
                              units={0: "đơn vị nguồn", 1: "inch (theo file)", 4: "mm"}.get(doc.units, "đơn vị nguồn"),
                              source_units=int(doc.units), brand_basis="block_name_rule_unverified", model_verified=False, view="Chưa xác nhận hướng nhìn",
                              source_block=name, source_file=source_file,
                              geometry_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        except Exception as exc:
            failures.append(dict(name=name, error=str(exc)))
    result = dict(version=1, source_dxf_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),
                  source_library=index["library_file"], items=items, failures=failures)
    (output / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(dict(exported=len(items), failed=len(failures))))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("source")
    p.add_argument("index")
    p.add_argument("output")
    p.add_argument("--brand", default="LS")
    p.add_argument("--source-file", default="@LS_recover.dwg")
    p.add_argument("--preserve-units", action="store_true")
    a = p.parse_args()
    export_layouts(a.source, a.index, a.output, a.brand, a.source_file, a.preserve_units)

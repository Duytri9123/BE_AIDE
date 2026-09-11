import asyncio
import json
import os
import sys

# Ensure app can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.brand import Brand
from app.models.device_category import DeviceCategory
from app.models.device_series import DeviceSeries
from app.models.device_model import DeviceModel

ALL_BRANDS = [
    "LS (standard)",
    "LS (premium)",
    "Schneider Electric",
    "Chint",
    "ABB",
    "Mitsubishi",
    "EMIC",
    "Samwha"
]

BRAND_MAP = {
    "ls_standard": "LS (standard)",
    "ls": "LS (standard)",
    "ls_premium": "LS (premium)",
    "schneider": "Schneider Electric",
    "chint": "Chint",
    "abb": "ABB",
    "mitsubishi": "Mitsubishi",
    "emic": "EMIC",
    "samwha": "Samwha"
}

async def seed_catalog():
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "catalog_data.json")
    if not os.path.exists(data_path):
        print(f"[ERROR] Data file not found: {data_path}")
        return

    with open(data_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    print(f"[INFO] Loaded {len(items)} items from {data_path}. Starting database seed...")

    async with AsyncSessionLocal() as session:
        # Cache brands
        brand_cache = {}
        stmt_brands = select(Brand)
        res_brands = await session.scalars(stmt_brands)
        for b in res_brands.all():
            brand_cache[b.name.lower()] = b

        # Ensure all brands in dropdown exist
        for bname in ALL_BRANDS:
            if bname.lower() not in brand_cache:
                new_brand = Brand(name=bname)
                session.add(new_brand)
                await session.flush()
                brand_cache[bname.lower()] = new_brand
                print(f"  + Created Brand: {bname}")

        # Cache categories
        cat_cache = {}
        stmt_cats = select(DeviceCategory)
        res_cats = await session.scalars(stmt_cats)
        for c in res_cats.all():
            cat_cache[c.name.upper()] = c

        # Ensure categories exist
        for cat_name in ["MCB", "MCCB", "ELCB", "RCBO", "RCCB", "AFDD", "Contactor", "ACB", "SPD", "Relay", "Thermal Relay", "METER", "CAPACITOR"]:
            if cat_name.upper() not in cat_cache:
                new_cat = DeviceCategory(name=cat_name)
                session.add(new_cat)
                await session.flush()
                cat_cache[cat_name.upper()] = new_cat
                print(f"  + Created DeviceCategory: {cat_name}")

        # Cache series
        series_cache = {}
        stmt_series = select(DeviceSeries)
        res_series = await session.scalars(stmt_series)
        for s in res_series.all():
            series_cache[(s.brand_id, s.device_category_id, s.name)] = s

        inserted_models = 0
        updated_models = 0

        # Cache existing models by SKU
        model_cache = {}
        stmt_models = select(DeviceModel)
        res_models = await session.scalars(stmt_models)
        for m in res_models.all():
            model_cache[m.sku] = m

        for item in items:
            raw_brand = item.get("brand", "ls_standard").lower()
            brand_name = BRAND_MAP.get(raw_brand, item.get("brand_display", raw_brand.upper() if raw_brand in ["emic", "abb"] else raw_brand.capitalize()))
            brand_obj = brand_cache.get(brand_name.lower())
            if not brand_obj:
                brand_obj = Brand(name=brand_name)
                session.add(brand_obj)
                await session.flush()
                brand_cache[brand_name.lower()] = brand_obj

            cat_name = item.get("t", "MCB").upper()
            cat_obj = cat_cache.get(cat_name)
            if not cat_obj:
                cat_obj = DeviceCategory(name=cat_name)
                session.add(cat_obj)
                await session.flush()
                cat_cache[cat_name] = cat_obj

            series_name = item.get("series") or "Standard"
            series_key = (brand_obj.id, cat_obj.id, series_name)
            series_obj = series_cache.get(series_key)
            if not series_obj:
                series_obj = DeviceSeries(
                    brand_id=brand_obj.id,
                    device_category_id=cat_obj.id,
                    name=series_name,
                    description=f"Dòng thiết bị {series_name} hãng {brand_name}"
                )
                session.add(series_obj)
                await session.flush()
                series_cache[series_key] = series_obj

            sku = item.get("ma", "")
            name = item.get("n", sku)
            price_val = item.get("g")
            price = float(price_val) if price_val is not None else 0.0

            dimensions = {
                "w": item.get("w"),
                "h": item.get("h"),
                "d": item.get("d"),
                "pitch": item.get("pitch"),
                "pole_w": item.get("pole_w"),
                "busbar_level": item.get("busbar_level"),
                "door_c1": item.get("door_c1"),
                "door_c2": item.get("door_c2")
            }

            parameters = {
                "p": item.get("p"),
                "in": item.get("in"),
                "icu": item.get("icu"),
                "idelta": item.get("idelta"),
                "ui": item.get("ui"),
                "uimp": item.get("uimp"),
                "kva": item.get("kva"),
                "meterKind": item.get("meterKind"),
                "frame": item.get("frame"),
                "barrier": item.get("barrier"),
                "clearance": item.get("clearance"),
                "creepage": item.get("creepage"),
                "busbar_holes": item.get("busbar_holes"),
                "mount_holes": item.get("mount_holes"),
                "_verified": item.get("_verified", True),
                "_pitch_src": item.get("_pitch_src"),
                "note": item.get("note")
            }

            if sku in model_cache:
                existing_m = model_cache[sku]
                existing_m.device_series_id = series_obj.id
                existing_m.name = name
                existing_m.price = price
                existing_m.dimensions = dimensions
                existing_m.parameters = parameters
                updated_models += 1
            else:
                new_model = DeviceModel(
                    device_series_id=series_obj.id,
                    sku=sku,
                    name=name,
                    price=price,
                    discount_pct=0.0,
                    dimensions=dimensions,
                    parameters=parameters
                )
                session.add(new_model)
                model_cache[sku] = new_model
                inserted_models += 1

        await session.commit()
        print(f"[SUCCESS] Database Seed Complete! Inserted: {inserted_models}, Updated: {updated_models}, Total in Catalog: {len(items)}")

if __name__ == "__main__":
    asyncio.run(seed_catalog())

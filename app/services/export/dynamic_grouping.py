from collections import OrderedDict

class DynamicGroupingEngine:
    @staticmethod
    def group_three_block(devices: list) -> OrderedDict:
        """Nhóm báo giá theo 3 block: Vỏ tủ -> Đầu vào -> Đầu ra."""
        groups = OrderedDict([
            ("Vỏ tủ & Phụ kiện", []),
            ("Đầu vào (Incomer)", []),
            ("Đầu ra (Feeders)", [])
        ])
        
        for d in devices:
            if d.get("is_incomer"):
                groups["Đầu vào (Incomer)"].append(d)
            elif d.get("is_enclosure"):
                groups["Vỏ tủ & Phụ kiện"].append(d)
            else:
                groups["Đầu ra (Feeders)"].append(d)
                
        return groups

    @staticmethod
    def group_functional(devices: list) -> OrderedDict:
        """Nhóm báo giá theo chức năng: Cơ khí -> Động lực -> Điều khiển."""
        groups = OrderedDict([
            ("Cơ khí", []),
            ("Động lực", []),
            ("Điều khiển", [])
        ])
        
        for d in devices:
            cat = d.get("category", "").lower()
            if cat in ["relay", "plc", "meter", "lamp", "button"]:
                groups["Điều khiển"].append(d)
            elif cat in ["enclosure", "busbar", "duct", "mounting"]:
                groups["Cơ khí"].append(d)
            else:
                groups["Động lực"].append(d)
                
        return groups

    @staticmethod
    def group_flat(devices: list) -> list:
        """Không nhóm, list thẳng."""
        return devices

    @staticmethod
    def _get_val(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    @staticmethod
    def _merge_accessories(*accessory_lists: list) -> list:
        """Merge attached accessories without losing their parent relationship."""
        merged = OrderedDict()
        for accessories in accessory_lists:
            for accessory in accessories or []:
                if hasattr(accessory, "model_dump"):
                    item = accessory.model_dump()
                else:
                    item = dict(accessory)
                key = (
                    str(item.get("code") or item.get("sku") or "").strip().casefold(),
                    str(item.get("name") or "").strip().casefold(),
                    str(item.get("spec") or "").strip().casefold(),
                )
                qty = float(item.get("quantity") or 1)
                if key in merged:
                    previous_qty = float(merged[key].get("quantity") or 1)
                    total = previous_qty + qty
                    merged[key]["quantity"] = int(total) if total.is_integer() else total
                else:
                    item["quantity"] = int(qty) if qty.is_integer() else qty
                    merged[key] = item
        return list(merged.values())

    @staticmethod
    def clean_device_name(name: str):
        """Loại bỏ ký hiệu lộ/nhánh như (Lộ M18), [Lộ 1], - Lộ M19... để gộp thiết bị cùng thông số."""
        if not name:
            return "", ""
        import re
        match = re.search(r'[\(\[\-]?\s*(?:lộ|feeder|nhánh)\s*([\w\d\-\.]+)\s*[\)\]]?', name, flags=re.IGNORECASE)
        branch_tag = match.group(0).strip("()[]- ") if match else ""
        cleaned = re.sub(r'[\(\[\-]?\s*(?:lộ|feeder|nhánh)\s*[\w\d\-\.]+\s*[\)\]]?', '', name, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned, branch_tag

    @staticmethod
    def merge_duplicates(devices: list) -> list:
        """Gộp các thiết bị giống nhau (cùng chủng loại, tên, thông số, mã hàng, hãng, đơn giá)
        thành 1 dòng, cộng dồn số lượng và tính lại thành tiền.
        Tự động tách nhãn Lộ/Nhánh (ví dụ: Lộ M18, Lộ M19) khỏi tên để gộp đúng.
        Hỗ trợ cả dict và Pydantic ExtractedDeviceSchema.
        """
        if not devices:
            return devices

        from pydantic import BaseModel

        merged = OrderedDict()
        for dev in devices:
            raw_name = str(DynamicGroupingEngine._get_val(dev, "name") or "").strip()
            clean_name, branch_tag = DynamicGroupingEngine.clean_device_name(raw_name)
            name_for_grouping = clean_name or raw_name

            cat = str(DynamicGroupingEngine._get_val(dev, "category") or "").strip()
            spec = str(DynamicGroupingEngine._get_val(dev, "spec") or "").strip()
            sku = str(DynamicGroupingEngine._get_val(dev, "sku") or DynamicGroupingEngine._get_val(dev, "part_number") or DynamicGroupingEngine._get_val(dev, "ma_hang") or "").strip()
            brand = str(DynamicGroupingEngine._get_val(dev, "brand") or DynamicGroupingEngine._get_val(dev, "xuat_xu") or DynamicGroupingEngine._get_val(dev, "origin") or "").strip()
            in_a = str(DynamicGroupingEngine._get_val(dev, "in_a") or "")
            poles = str(DynamicGroupingEngine._get_val(dev, "poles") or "")
            unit_price = DynamicGroupingEngine._get_val(dev, "unit_price") or DynamicGroupingEngine._get_val(dev, "don_gia") or DynamicGroupingEngine._get_val(dev, "price") or 0

            norm_name = name_for_grouping.lower()
            norm_cat = cat.lower()
            norm_spec = spec.lower()
            norm_sku = sku.lower()
            norm_brand = brand.lower().replace(" electric", "")

            panel = str(DynamicGroupingEngine._get_val(dev, "panel_code") or "").strip().casefold()
            icu = DynamicGroupingEngine._get_val(dev, "icu_ka")
            key = (panel, norm_cat, norm_name, norm_spec, norm_sku, norm_brand, in_a, poles, icu, unit_price)

            is_pydantic = isinstance(dev, BaseModel)
            qty = float(DynamicGroupingEngine._get_val(dev, "quantity") or DynamicGroupingEngine._get_val(dev, "so_luong") or 1)
            raw_note = str(DynamicGroupingEngine._get_val(dev, "notes") or DynamicGroupingEngine._get_val(dev, "ghi_chu") or "").strip()
            
            # Gộp nhãn nhánh vào note nếu có
            note = raw_note
            if branch_tag and branch_tag not in note:
                note = f"{note} ({branch_tag})" if note else branch_tag

            if key in merged:
                existing = merged[key]
                old_qty = float(DynamicGroupingEngine._get_val(existing, "quantity") or DynamicGroupingEngine._get_val(existing, "so_luong") or 1)
                new_qty = old_qty + qty

                old_note = str(DynamicGroupingEngine._get_val(existing, "notes") or DynamicGroupingEngine._get_val(existing, "ghi_chu") or "").strip()
                combined_note = old_note
                if note and note not in old_note:
                    combined_note = f"{old_note}; {note}" if old_note else note

                combined_accessories = DynamicGroupingEngine._merge_accessories(
                    DynamicGroupingEngine._get_val(existing, "accompanying_accessories") or [],
                    DynamicGroupingEngine._get_val(dev, "accompanying_accessories") or [],
                )

                if is_pydantic:
                    updates = {
                        "name": name_for_grouping,
                        "quantity": int(new_qty) if new_qty.is_integer() else new_qty
                    }
                    if combined_note:
                        updates["notes"] = combined_note
                    if combined_accessories:
                        updates["accompanying_accessories"] = combined_accessories
                    merged[key] = existing.model_copy(update=updates)
                else:
                    existing["name"] = name_for_grouping
                    existing["quantity"] = int(new_qty) if new_qty.is_integer() else new_qty
                    if "so_luong" in existing:
                        existing["so_luong"] = new_qty
                    if "line_total" in existing:
                        existing["line_total"] = new_qty * float(unit_price)
                    if "thanh_tien" in existing:
                        existing["thanh_tien"] = new_qty * float(unit_price)
                    if "notes" in existing:
                        existing["notes"] = combined_note
                    if "ghi_chu" in existing:
                        existing["ghi_chu"] = combined_note
                    if combined_accessories:
                        existing["accompanying_accessories"] = combined_accessories
            else:
                if is_pydantic:
                    merged[key] = dev.model_copy(update={"name": name_for_grouping, "notes": note} if note else {"name": name_for_grouping})
                else:
                    item_copy = dict(dev)
                    item_copy["name"] = name_for_grouping
                    if unit_price:
                        item_copy["line_total"] = qty * float(unit_price)
                        item_copy["thanh_tien"] = qty * float(unit_price)
                    if note:
                        if "notes" in item_copy or "ghi_chu" not in item_copy:
                            item_copy["notes"] = note
                    merged[key] = item_copy

        return list(merged.values())

    @staticmethod
    def group(devices: list, layout: str) -> OrderedDict | list:
        """Định tuyến layout nhóm dữ liệu."""
        if layout == "three_block":
            return DynamicGroupingEngine.group_three_block(devices)
        elif layout == "functional":
            return DynamicGroupingEngine.group_functional(devices)
        return DynamicGroupingEngine.group_flat(devices)

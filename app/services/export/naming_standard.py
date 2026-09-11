class NamingStandardService:
    @staticmethod
    def standardize_name(device: dict) -> str:
        """Chuẩn hóa tên thiết bị: [Category] [Poles]P [In]A [Icu]kA [Brand]"""
        category = device.get("category", "Unknown")
        poles = device.get("poles", 3)
        in_a = device.get("in_a", 0)
        icu_ka = device.get("icu_ka", 0)
        brand = device.get("brand", "UnknownBrand")
        
        parts = [category]
        if poles > 0:
            parts.append(f"{poles}P")
        if in_a > 0:
            parts.append(f"{in_a}A")
        if icu_ka > 0:
            parts.append(f"{icu_ka}kA")
        parts.append(brand)
        
        return " ".join(parts)

    @staticmethod
    def generate_item_code(category: str, index: int) -> str:
        """Tạo mã định danh duy nhất (item code), VD: MCCB-001"""
        cat = str(category).upper()[:4] if category else "ITEM"
        return f"{cat}-{index:03d}"

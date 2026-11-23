"""Fix takeoff_catalog.py to parse specs from name+spec combined, not just spec."""
import re

path = 'app/services/ai/takeoff_catalog.py'
content = open(path, encoding='utf-8').read()

# Find the exact block
marker = 'Bổ sung thông số thiếu từ trường spec'
idx = content.find(marker)
if idx < 0:
    print("MARKER NOT FOUND")
    exit(1)

# Print what's there for debug
print("Found at index:", idx)
# Find block start (back to 'device = Extract')
block_start = content.rfind('        device = ExtractedDeviceSchema.model_validate(row)', 0, idx)
# Find block end (up to 'norm_cat = _normalize')
block_end = content.find('\n        norm_cat = _normalize_device_category(device)', idx)
print("Block:")
print(repr(content[block_start:block_end]))

old_block = content[block_start:block_end]
new_block = '''        device = ExtractedDeviceSchema.model_validate(row)

        # Bổ sung thông số thiếu: parse từ cả name + spec + rated_current
        combined_text = f"{device.name or ''} {device.spec or ''}"
        # Hỗ trợ rated_current field (AI có thể gửi thay cho in_a)
        if not device.in_a and row.get('rated_current'):
            try:
                device.in_a = float(str(row['rated_current']).replace(',', '.').split()[0])
            except (ValueError, TypeError):
                pass
        for field, pattern in [
            ('in_a',   r'(?<![\d.])(\d+(?:[.,]\d+)?)\s*A\b'),
            ('poles',  r'\b([1-4])\s*[Pp]\b'),
            ('icu_ka', r'(?<![\d.])(\d+(?:[.,]\d+)?)\s*kA\b'),
        ]:
            if not getattr(device, field):
                m = re.search(pattern, combined_text, re.I)
                if m:
                    setattr(
                        device,
                        field,
                        int(m[1]) if field == 'poles' else float(m[1].replace(',', '.')),
                    )'''

new_content = content[:block_start] + new_block + content[block_end:]
open(path, 'w', encoding='utf-8').write(new_content)
print("DONE - file updated")

"""Fix poles pattern to support 'pha' (Vietnamese) and also fix MCCB poles detection."""
path = 'app/services/ai/takeoff_catalog.py'
content = open(path, encoding='utf-8').read()

# Add extra poles-from-pha parsing after the main for loop
# Also add "3 pha" -> 3P mapping
old = "        norm_cat = _normalize_device_category(device)"

new = """        # Bổ sung poles từ "X pha" (tiếng Việt) nếu chưa có
        if not device.poles:
            m_pha = re.search(r'\\b([1-4])\\s*pha\\b', combined_text, re.I)
            if m_pha:
                device.poles = int(m_pha.group(1))
            elif re.search(r'\\b(ba|three|3)\\s*pha\\b', combined_text, re.I):
                device.poles = 3
            elif re.search(r'\\b(hai|two|2)\\s*pha\\b', combined_text, re.I):
                device.poles = 2

        norm_cat = _normalize_device_category(device)"""

content = content.replace(old, new, 1)
open(path, 'w', encoding='utf-8').write(content)
print("DONE")

# Verify
count = content.count("norm_cat = _normalize_device_category(device)")
print(f"norm_cat occurrences: {count} (expected 1)")

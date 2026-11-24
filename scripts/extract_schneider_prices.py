import fitz
import re
import json

doc = fitz.open(r'c:\Users\admin\Downloads\[SMALL SIZE] BANG GIA DAI LY 2026 (12).pdf')
print("Total pages in Schneider PDF:", len(doc))

extracted_prices = {} # sku -> price

# Regex for Schneider order code (e.g. A9K27106, EZ9D34610, LV510300, LC1D09M7, EZC100N3015...)
sku_pattern = re.compile(r'\b([A-Z0-9]{5,15})\b')
# Regex for price (e.g. 1.072.500 or 841500)
price_pattern = re.compile(r'(\d{1,3}(?:\.\d{3})+|\d{4,9})')

for page_idx in range(len(doc)):
    page = doc[page_idx]
    tab_finder = page.find_tables()
    for tab in tab_finder.tables:
        df = tab.extract()
        for row in df:
            for cell in row:
                if not cell:
                    continue
                lines = [l.strip() for l in str(cell).split('\n') if l.strip()]
                # check pairs
                for i in range(len(lines)):
                    m_sku = sku_pattern.match(lines[i])
                    if m_sku:
                        sku = m_sku.group(1)
                        # look for price in subsequent lines or in other cells
                        pass

print(f"Testing extraction...")

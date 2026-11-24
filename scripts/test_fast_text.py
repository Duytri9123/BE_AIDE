import fitz
import time

t0 = time.time()
doc = fitz.open(r'c:\Users\admin\Downloads\[SMALL SIZE] BANG GIA DAI LY 2026 (12).pdf')
total_chars = 0
for i, page in enumerate(doc):
    t = page.get_text()
    total_chars += len(t)
print(f"Extracted {total_chars} chars across {len(doc)} pages in {time.time()-t0:.2f} seconds!")

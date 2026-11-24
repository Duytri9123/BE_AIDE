import fitz
import os

pdf_files = [
    r'c:\Users\admin\Downloads\BG - MCCB -27% MCB 34%.pdf',
    r'c:\Users\admin\Downloads\BG - MCB 34% - 20240710.pdf',
    r'c:\Users\admin\Downloads\[SMALL SIZE] BANG GIA DAI LY 2026 (12).pdf'
]

for path in pdf_files:
    print(f"\n==========================================")
    print(f"FILE: {os.path.basename(path)}")
    print(f"==========================================")
    if not os.path.exists(path):
        print("NOT FOUND")
        continue
    doc = fitz.open(path)
    print(f"Total pages: {len(doc)}")
    for page_num in range(min(5, len(doc))):
        page = doc[page_num]
        text = page.get_text()
        print(f"\n--- Page {page_num + 1} (text length: {len(text.strip())}) ---")
        if text.strip():
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            for line in lines[:10]:
                print("  ", line)
        else:
            images = page.get_images()
            print(f"  [Scanned/Image page: {len(images)} images]")

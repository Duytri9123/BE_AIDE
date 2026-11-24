import fitz

doc = fitz.open(r'c:\Users\admin\Downloads\[SMALL SIZE] BANG GIA DAI LY 2026 (12).pdf')
print("Total pages:", len(doc))

toc = doc.get_toc()
print(f"Table of contents ({len(toc)} entries):")
for item in toc[:35]:
    print(item)

if not toc:
    print("No TOC in metadata. Scanning page titles...")
    for i in range(len(doc)):
        text = doc[i].get_text()
        first_lines = [l.strip() for l in text.split('\n') if l.strip()][:3]
        if first_lines:
            print(f"Page {i+1}: {' | '.join(first_lines)}")

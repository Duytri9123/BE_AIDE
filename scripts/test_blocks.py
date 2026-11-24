import fitz

doc = fitz.open(r'c:\Users\admin\Downloads\[SMALL SIZE] BANG GIA DAI LY 2026 (12).pdf')
p = doc[28]
blocks = p.get_text("blocks")
# Sort by y0 then x0
sorted_blocks = sorted(blocks, key=lambda b: (round(b[1], 0), b[0]))
for b in sorted_blocks[:30]:
    t = b[4].strip().replace('\n', ' ')
    print(f"y={b[1]:.1f}, x={b[0]:.1f}: {t}")

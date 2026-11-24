import fitz

doc = fitz.open(r'c:\Users\admin\Downloads\[SMALL SIZE] BANG GIA DAI LY 2026 (12).pdf')

for page_num in [28, 29, 30, 31, 34, 39, 40, 41, 48, 50, 52]:
    p = doc[page_num - 1]
    tab_finder = p.find_tables()
    tables = tab_finder.tables
    print(f"\n--- PAGE {page_num} (tables found: {len(tables)}) ---")
    if tables:
        for t_idx, tab in enumerate(tables):
            df = tab.extract()
            print(f"Table {t_idx+1}: {len(df)} rows, {len(df[0]) if df else 0} cols")
            for row in df[:5]:
                print("  ", row)
    else:
        lines = [l.strip() for l in p.get_text().split('\n') if l.strip()]
        print("Text sample:", lines[:15])

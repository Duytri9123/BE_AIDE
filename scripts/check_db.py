import sqlite3

conn = sqlite3.connect("webbaogia.db")
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print(f"Total tables: {len(tables)}")
for t in sorted(tables):
    try:
        c.execute(f'SELECT count(*) FROM "{t}"')
        cnt = c.fetchone()[0]
        if cnt > 0:
            print(f"{t}: {cnt}")
    except Exception as e:
        print(f"{t}: error {e}")

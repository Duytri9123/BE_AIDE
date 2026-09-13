import sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("webbaogia.db")
c = conn.cursor()
c.execute("SELECT id, name, type, is_active, length(content) FROM prompt_templates")
for r in c.fetchall():
    print(r)

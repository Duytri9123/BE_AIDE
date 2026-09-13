import sqlite3

conn = sqlite3.connect("webbaogia.db")
c = conn.cursor()
c.execute("PRAGMA table_info(users)")
for col in c.fetchall():
    print(col)
c.execute("SELECT * FROM users")
for r in c.fetchall():
    print(r)

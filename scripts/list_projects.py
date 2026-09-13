import sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("webbaogia.db")
c = conn.cursor()
c.execute("SELECT id, name, user_id FROM projects")
rows = c.fetchall()
print(f"Total projects: {len(rows)}")
for r in rows:
    print(r)

c.execute("SELECT id, project_id, filename, file_path FROM project_files")
files = c.fetchall()
print(f"Total project_files: {len(files)}")
for f in files:
    print(f)

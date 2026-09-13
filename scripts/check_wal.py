import sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("webbaogia.db")
c = conn.cursor()
c.execute("PRAGMA journal_mode")
print("Journal mode:", c.fetchone())
c.execute("PRAGMA wal_checkpoint(PASSIVE)")
print("Checkpoint:", c.fetchone())

c.execute("SELECT id, name, user_id FROM projects ORDER BY id DESC LIMIT 5")
print("Projects:", c.fetchall())

c.execute("SELECT id, filename, file_path FROM project_files ORDER BY id DESC LIMIT 5")
print("Files:", c.fetchall())

c.execute("SELECT id, session_id, iteration_number, length(ai_parsed_devices) FROM analysis_iterations ORDER BY id DESC LIMIT 5")
print("Iterations:", c.fetchall())

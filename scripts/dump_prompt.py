import sqlite3, sys
sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("webbaogia.db")
c = conn.cursor()
c.execute("SELECT content FROM prompt_templates WHERE id=1")
content = c.fetchone()[0]
with open("scripts/db_prompt_content.txt", "w", encoding="utf-8") as f:
    f.write(content)
print(f"Written prompt content, length: {len(content)}")
print("First 500 chars:\n", content[:500])
print("\nLast 500 chars:\n", content[-500:])

import sqlite3, json, sys
sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("webbaogia.db")
c = conn.cursor()
c.execute("SELECT id, session_id, iteration_number, length(ai_parsed_devices), ai_parsed_devices FROM analysis_iterations ORDER BY id DESC LIMIT 1")
r = c.fetchone()
print(f"Latest Iteration ID: {r[0]} (Session: {r[1]}, Iteration Number: {r[2]}, Size: {r[3]} bytes)")
devs = json.loads(r[4])
print(f"Total devices stored: {len(devs)}")
for idx, d in enumerate(devs[:15]):
    cat = d.get("category")
    name = d.get("name")
    spec = d.get("spec")
    ina = d.get("in_a")
    brand = d.get("brand")
    box = d.get("box_2d")
    has_ev = bool(d.get("evidence_image"))
    print(f"  {idx+1:2d}. [{cat:6s}] {name:40s} | Spec: {spec:18s} | In: {str(ina):>5s}A | Brand: '{brand}' | Box: {box} | Evidence: {has_ev}")

import re

path = 'app/api/v1/endpoints/el_agent.py'
content = open(path, encoding='utf-8').read()
changes = []

# Fix 1: incomplete evidence block (~line 1983)
pat1 = re.compile(
    r"        if incomplete:\n"
    r"            return \{[^\n]*verification_feedback[^\n]*device_evidence[^\n]*\}"
)
repl1 = (
    "        if incomplete:\n"
    "            # Soft-flag: đánh dấu thiếu minh chứng nhưng không block lưu\n"
    "            for _d in devices_data:\n"
    "                _tag = str(_d.get('tag') or _d.get('name') or '')\n"
    "                if any(_tag in item for item in incomplete):\n"
    "                    _d.setdefault('evidence_region', {})['status'] = 'needs_review'\n"
    "                    _d['_evidence_note'] = 'Chua du minh chung; can ra soat.'"
)
m1 = pat1.search(content)
if m1:
    content = content[:m1.start()] + repl1 + content[m1.end():]
    changes.append("Fix 1 OK: incomplete evidence soft-flag")
else:
    changes.append("Fix 1 FAILED")

# Fix 2: meter_type_is_grounded block (~line 1997)
pat2 = re.compile(
    r"    if any\(not meter_type_is_grounded\(d\) for d in devices_data\):\n"
    r"        return \{[^\n]*verification_feedback[^\n]*\}"
)
repl2 = (
    "    # Soft: meter type unconfirmed -> flag, khong block\n"
    "    for d in devices_data:\n"
    "        if not meter_type_is_grounded(d):\n"
    "            d.setdefault('evidence_region', {}).setdefault('status', 'needs_review')"
)
m2 = pat2.search(content)
if m2:
    content = content[:m2.start()] + repl2 + content[m2.end():]
    changes.append("Fix 2 OK: meter_type soft-flag")
else:
    changes.append("Fix 2 FAILED")

# Fix 3: grounded_devices check (~line 2000)
pat3 = re.compile(
    r"    if len\(grounded_devices\) != len\(devices_data\):\n"
    r"        return \{[^\n]*verification_feedback[^\n]*\}\n"
    r"    devices_data = grounded_devices"
)
repl3 = (
    "    if len(grounded_devices) != len(devices_data):\n"
    "        # Soft: flag ungrounded, khong block\n"
    "        grounded_set = set(id(d) for d in grounded_devices)\n"
    "        for d in devices_data:\n"
    "            if id(d) not in grounded_set:\n"
    "                d.setdefault('evidence_region', {})['status'] = 'needs_review'\n"
    "                d.setdefault('_evidence_note', 'Thiet bi chua co minh chung vi tri; can ra soat.')\n"
    "    devices_data = grounded_devices + [\n"
    "        d for d in devices_data\n"
    "        if id(d) not in set(id(x) for x in grounded_devices)\n"
    "        and d.get('evidence_region', {}).get('status') == 'needs_review'\n"
    "    ]"
)
m3 = pat3.search(content)
if m3:
    content = content[:m3.start()] + repl3 + content[m3.end():]
    changes.append("Fix 3 OK: grounded_devices soft-flag")
else:
    changes.append("Fix 3 FAILED")

# Fix 4: audit_cad_ratings fail (~line 2010)
pat4 = re.compile(
    r"            if not audit\['passed'\]:\n"
    r"                return \{[^\n]*verification_feedback[^\n]*\}"
)
repl4 = (
    "            if not audit['passed']:\n"
    "                # Soft: log issues, flag devices, khong block\n"
    "                logger.warning('CAD audit issues (soft): %s', audit.get('issues'))\n"
    "                for _d in devices_data:\n"
    "                    if _d.get('source_file_id') == file.id:\n"
    "                        _d.setdefault('evidence_region', {}).setdefault('status', 'needs_review')"
)
m4 = pat4.search(content)
if m4:
    content = content[:m4.start()] + repl4 + content[m4.end():]
    changes.append("Fix 4 OK: audit_cad_ratings soft-flag")
else:
    changes.append("Fix 4 FAILED")

# Fix 5: verify_takeoff fail (~line 2053)
pat5 = re.compile(
    r"        if not review\['passed'\]:\n"
    r"            return \{[^\n]*verification_feedback[^\n]*review\['feedback'\][^\n]*\}"
)
repl5 = (
    "        if not review['passed']:\n"
    "            # Soft: flag devices needs_review thay vi block\n"
    "            logger.warning('Visual verification soft-save: %s', str(review.get('feedback', ''))[:200])\n"
    "            for _d in devices_data:\n"
    "                _d.setdefault('evidence_region', {}).setdefault('status', 'needs_review')"
)
m5 = pat5.search(content)
if m5:
    content = content[:m5.start()] + repl5 + content[m5.end():]
    changes.append("Fix 5 OK: verify_takeoff soft-flag")
else:
    changes.append("Fix 5 FAILED")

open(path, 'w', encoding='utf-8').write(content)
for c in changes:
    print(c)
print('DONE')

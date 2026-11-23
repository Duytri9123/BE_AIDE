import re

# Test patterns on typical device names
tests = [
    'MCB 3P-32A Icu=6kA',
    'MCCB 3P 100A 25kA',
    'Aptomat 2P 16A',
    'CB 1P-10A',
    'Contactor 3P 32A',
    'MCB 3 Pha 25A',
    'Khoi tu dong 32A 3P',
]

patterns = [
    ('in_a',   r'(?<![\d.])(\d+(?:[.,]\d+)?)\s*A\b'),
    ('poles',  r'\b([1-4])\s*[Pp]\b'),
    ('icu_ka', r'(?<![\d.])(\d+(?:[.,]\d+)?)\s*kA\b'),
]

for text in tests:
    results = {}
    for field, pat in patterns:
        m = re.search(pat, text, re.I)
        results[field] = m.group() if m else None
    print(f'{text!r:40} -> {results}')

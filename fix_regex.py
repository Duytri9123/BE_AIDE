"""Fix regex escape sequences in takeoff_catalog.py"""
path = 'app/services/ai/takeoff_catalog.py'
content = open(path, encoding='utf-8').read()

old_patterns = """        for field, pattern in [
            ('in_a',   r'(?<![\d.])(\d+(?:[.,]\d+)?)\s*A\b'),
            ('poles',  r'\b([1-4])\s*[Pp]\b'),
            ('icu_ka', r'(?<![\d.])(\d+(?:[.,]\d+)?)\s*kA\b'),
        ]:"""

# Check if old with broken escape exists
broken = """        for field, pattern in [
            ('in_a',   r'(?<![\d.])(\d+(?:[.,]\d+)?)\s*A\\b'),
            ('poles',  r'\b([1-4])\s*[Pp]\b'),
            ('icu_ka', r'(?<![\d.])(\d+(?:[.,]\d+)?)\s*kA\\b'),
        ]:"""

new_patterns = """        for field, pattern in [
            ('in_a',   r'(?<![\\d.])(\\d+(?:[.,]\\d+)?)\\s*A\\b'),
            ('poles',  r'\\b([1-4])\\s*[Pp]\\b'),
            ('icu_ka', r'(?<![\\d.])(\\d+(?:[.,]\\d+)?)\\s*kA\\b'),
        ]:"""

# Find the for field, pattern block
import re
# Replace raw pattern lines precisely
pattern_block_re = re.compile(
    r"        for field, pattern in \[\n"
    r"            \('in_a',.*?\n"
    r"            \('poles',.*?\n"
    r"            \('icu_ka',.*?\n"
    r"        \]:",
    re.DOTALL
)
match = pattern_block_re.search(content)
if match:
    print("Found pattern block:", repr(match.group()))
    content = content[:match.start()] + new_patterns + content[match.end():]
    open(path, 'w', encoding='utf-8').write(content)
    print("DONE - regex patterns fixed")
else:
    print("Pattern block NOT FOUND")
    # Show context
    idx = content.find("for field, pattern in")
    print(repr(content[idx:idx+300]))

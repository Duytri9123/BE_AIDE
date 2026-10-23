"""Text normalization without loading the CAD engine or connecting to Redis."""
import unicodedata


def strip_accents(s: str) -> str:
    if not s:
        return ''
    s = str(s).replace('đ', 'd').replace('Đ', 'D')
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')

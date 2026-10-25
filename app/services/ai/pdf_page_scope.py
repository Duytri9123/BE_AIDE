"""Resolve explicit page scope before falling back to the viewer's page."""
import re
import unicodedata

PREFIX = r'\b(?:trang|pages?|sheets?|p\.)\s*(?:so\s*)?'
PAGE_SET = PREFIX + r'\d+(?:\s*(?:-|den|to|,|&|va)\s*(?:(?:trang|pages?|sheets?)\s*)?\d+)*'
EXCLUSION = r'\b(?:bo qua|loai bo|khong (?:boc tach|phan tich|chon)|ngoai tru|tru)\s+(?:cac\s+)?' + PAGE_SET


def _numbers(text, total_pages):
    selected = set()
    for first, last in re.findall(PREFIX + r'(\d+)\s*(?:-|den|to)\s*(?:trang\s*)?(\d+)', text):
        selected.update(range(max(1, int(first)), min(total_pages, int(last)) + 1))
    for group in re.findall(PREFIX + r'(\d+(?:\s*(?:,|&|va)\s*\d+)+)', text):
        selected.update(int(value) for value in re.findall(r'\d+', group) if 1 <= int(value) <= total_pages)
    selected.update(int(value) for value in re.findall(PREFIX + r'(\d+)\b', text) if 1 <= int(value) <= total_pages)
    return selected


def requested_pdf_pages(prompt, total_pages, target_page=None):
    text = ''.join(c for c in unicodedata.normalize('NFD', prompt.lower().replace('đ', 'd')) if not unicodedata.combining(c))
    exclusions = re.findall(EXCLUSION, text)
    positive = re.sub(EXCLUSION, '', text)
    excluded = set().union(*(_numbers(fragment, total_pages) for fragment in exclusions)) if exclusions else set()
    all_pages = bool(re.search(r'\b(?:tat ca|toan bo|ca hai|ca 2|all)\s+(?:cac\s+)?(?:trang|pages?)\b', positive))
    explicit = bool(re.search(PREFIX + r'\d+', positive))
    if all_pages or (exclusions and not explicit):
        selected = set(range(1, total_pages + 1))
    elif explicit:
        selected = _numbers(positive, total_pages)
    else:
        selected = {target_page} if target_page and 1 <= target_page <= total_pages else set()
    selected -= excluded
    if (all_pages or explicit or exclusions) and not selected:
        raise ValueError('Phạm vi yêu cầu không có trang PDF hợp lệ để bóc tách; hãy kiểm tra lại số trang.')
    return sorted(selected)

"""Select PDF pages from the user's request, never from generated assessment notes."""
import re
import unicodedata

def requested_pdf_pages(prompt, total_pages, target_page=None):
    text = ''.join(c for c in unicodedata.normalize('NFD', prompt.lower().replace('đ','d')) if not unicodedata.combining(c))
    if re.search(r'\b(?:tat ca|toan bo|ca hai|ca 2|all)\s+(?:cac\s+)?(?:trang|pages?)\b', text) or re.search(r'\bca hai trang\b',text):
        return list(range(1,total_pages+1))
    selected={target_page} if target_page and 1<=target_page<=total_pages else set()
    prefix=r'\b(?:trang|page|sheet|p\.)\s*(?:so\s*)?'
    for start,end in re.findall(prefix+r'(\d+)\s*(?:-|den|to)\s*(?:trang\s*)?(\d+)',text):
        selected.update(range(max(1,int(start)),min(total_pages,int(end))+1))
    for group in re.findall(prefix+r'(\d+(?:\s*(?:,|&|va)\s*\d+)+)',text):
        selected.update(int(v) for v in re.findall(r'\d+',group) if 1<=int(v)<=total_pages)
    selected.update(int(v) for v in re.findall(prefix+r'(\d+)\b',text) if 1<=int(v)<=total_pages)
    return sorted(selected)

"""Unify orthographic aliases, without fuzzy matching different panel codes."""
import re
import unicodedata

def panel_identity(code):
    text=unicodedata.normalize('NFD',str(code or '').upper().replace('Đ','D'))
    return re.sub(r'\s+','', ''.join(c for c in text if not unicodedata.combining(c))).replace('–','-')

def normalize_panel_identities(devices, panels=None):
    def get(row,key): return row.get(key) if isinstance(row,dict) else getattr(row,key,None)
    def put(row,key,value):
        if isinstance(row,dict): row[key]=value
        else: setattr(row,key,value)
    aliases={}
    for row in [*(panels or []),*devices]:
        code=str(get(row,'panel_code') or '').strip()
        if code: aliases.setdefault(panel_identity(code),code)
    for row in [*(panels or []),*devices]:
        code=str(get(row,'panel_code') or '').strip()
        if code: put(row,'panel_code',aliases[panel_identity(code)])
    return devices

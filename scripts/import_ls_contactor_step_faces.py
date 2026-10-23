"""Publish only named LS coil/pole variants backed by the corresponding STEP."""
import re,json
from pathlib import Path
from import_ls_step_family import import_family,ROOT
from app.services.catalog_product_sections import current_kinds
JOBS=[('50324',['MR-4'],'AC',None),('50326',['MR-4'],'DC',None),('50307',['MC-32a','MC-40a'],'AC','3P'),('50309',['MC-32a','MC-40a'],'DC','3P'),('50313',['MC-50a','MC-65a'],'AC','3P'),('50315',['MC-50a','MC-65a'],'DC','3P'),('50317',['MC-75a','MC-85a','MC-100a'],'AC','3P'),('50319',['MC-75a','MC-85a','MC-100a'],'DC','3P'),('50321',['MC-130a','MC-150a'],'AC','3P'),('50335',['MC-185a','MC-225a'],'AC','3P'),('51933',['MC-265a','MC-330a','MC-400a'],'AC','3P'),('50339',['MC-500a','MC-630a','MC-800a'],'AC','3P'),('50364',['MC-100a','MC-130a','MC-150a','MC-185a','MC-225a'],'AC','4P'),('50357',['MC-265a','MC-330a','MC-400a'],'AC','4P'),('50359',['MC-500a','MC-630a','MC-800a'],'AC','4P')]
JOBS += [('50301',['MC-6a','MC-9a','MC-12a','MC-18a'],'AC','3P'),('50304',['MC-9b','MC-12b','MC-18b','MC-22b'],'AC','3P'),('55766',['MC-9b','MC-12b','MC-18b','MC-22b'],'DC','3P')]
JOBS += [('50349',['MC-6a','MC-9a','MC-12a','MC-18a'],'AC','4P'),('50351',['MC-22a'],'AC','4P'),('50354',['MC-32a','MC-40a'],'AC','4P'),('50362',['MC-50a','MC-65a','MC-75a','MC-85a'],'AC','4P')]

def choice(r,models,coil,poles):
 if r.get('category')!='CONTACTOR':return False
 m=re.match(r'^(MR-4|MC-\d+[ab])(?=\s|$|/)',r['sku'])
 if not m or m[1] not in models or ('/4' in r['sku'])!=(poles=='4P'):return False
 text=' '.join([r['sku'],str(r.get('group') or ''),*[str(v) for v in (r.get('specifications') or {}).values()]])
 return current_kinds(text)=={coil}
if __name__=='__main__':
 import sys
 for ident,models,coil,poles in JOBS:
  if len(sys.argv)>1 and ident not in sys.argv[1:]:continue
  name='LS · '+('Rơ le contactor' if models==['MR-4'] else 'Contactor')+' · '+' / '.join(models)+' · '+(poles+' · ' if poles else '')+'Cuộn '+coil
  import_family(ident,'CONTACTOR',models,poles,lambda r:choice(r,models,coil,poles),spec={'Loại cuộn hút':coil,**({'Tiếp điểm phụ':'2a2b'} if ident in ['50307','50309','50313','50315','50317','50319'] else {})},name=name)

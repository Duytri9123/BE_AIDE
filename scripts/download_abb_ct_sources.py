"""Acquire current ABB CT1M drawing packages, preserving supplier evidence."""
import concurrent.futures,hashlib,io,json,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'data/CatalogTB/BienDong/ABB/NguonBenNgoai'
SOURCES={'CT1M-2':'9AKK108470A9294','CT1M-3':'9AKK108470A9323','CT1M-4':'9AKK108470A9324',
'CT1M-5':'9AKK108470A9325','CT1M-6':'9AKK108470A9326','CT1M-7':'9AKK108470A9327',
'CT1M-8':'9AKK108470A9328','CT1M-10':'9AKK108470A9329','CT1M-12':'9AKK108470A9330',
'CT1M-S-30':'9AKK108470A9331','CT1M-S-80':'9AKK108470A9332','CT1M-S-120':'9AKK108470A9333'}

def acquire(pair):
 family,uid=pair;folder=ROOT/family;folder.mkdir(parents=True,exist_ok=True)
 url=f'https://search.abb.com/library/Download.aspx?DocumentID={uid}&LanguageCode=en&DocumentPartId=&Action=Launch'
 package=folder/'supplier.zip'
 if not package.exists():
  with urllib.request.urlopen(url,timeout=50) as response:content=response.read()
  if not zipfile.is_zipfile(io.BytesIO(content)):raise ValueError('Not a ZIP: '+family)
  package.write_bytes(content)
 metadata={'family':family,'document_id':uid,'source_url':url,'sha256':hashlib.sha256(package.read_bytes()).hexdigest(),'checked_at':'2026-10-20','files':[]}
 with zipfile.ZipFile(package) as archive:
  for member in archive.infolist():
   metadata['files'].append(member.filename)
   if member.is_dir():continue
   if Path(member.filename).suffix.lower() not in {'.dxf','.dwg','.pdf'}:continue
   target=folder/Path(member.filename.replace('\\','/')).name
   target.write_bytes(archive.read(member))
 (folder/'source.json').write_text(json.dumps(metadata,indent=2),encoding='utf8')
 return metadata

if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
  for item in executor.map(acquire,SOURCES.items()):print(json.dumps(item))

"""Acquire product-linked ABB S200 CAD documents found in its public download service."""
import hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data/CatalogTB/ABB/NguonBenNgoai'
def main():
 groups=json.loads((ROOT/'tmp/abb-s201-documents.json').read_text(encoding='utf8'))
 docs=[v for g in groups for v in g['Value'] if v.get('TranslatedDocumentKind')=='CAD outline drawing' and v.get('RepresentationFileNameSuffix') in {'stp','dwg'}]
 for v in docs:
  uid=v['DocumentID'];folder=OUT/uid;folder.mkdir(parents=True,exist_ok=True)
  url='https://search.abb.com/library/Download.aspx?DocumentID='+uid+'&LanguageCode=en&DocumentPartId=&Action=Launch'
  target=folder/('source.step' if v['RepresentationFileNameSuffix']=='stp' else 'source.dwg')
  if not target.exists():
   data=urllib.request.urlopen(url,timeout=60).read();assert data.startswith(b'ISO-10303-21' if target.suffix=='.step' else b'AC10');target.write_bytes(data)
  (folder/'source.json').write_text(json.dumps({'source_url':url,'source_page':'https://www.abbconnect.nl/Details/Index.aspx/2CDS251001R0061?ShowBorder=True&country=nl&languageCode=en','document_id':uid,'title':v['Title'],'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'checked_at':'2026-10-22'},indent=2),encoding='utf8')
  print(uid,v['Title'],target.stat().st_size,flush=True)
if __name__=='__main__':main()

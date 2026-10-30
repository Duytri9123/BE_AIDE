"""Wrap one existing projection as one selectable block without changing its entities."""
import io,re,hashlib,json
from pathlib import Path
from functools import lru_cache
import ezdxf

ROOT=Path(__file__).resolve().parents[3]/'data/CatalogTB'
MANIFEST=ROOT/'_agent_index/ls_device_exports/manifest.json'

@lru_cache(maxsize=2)
def _prepared_exports(revision):
 return {r['source_sha256']:r for r in json.loads(MANIFEST.read_text(encoding='utf8'))['items']}

def native_visibility_insert(doc):
 space=list(doc.modelspace())
 if len(space)!=1 or space[0].dxftype()!='INSERT':return False
 block=doc.blocks.get(space[0].dxf.name)
 if block is None:return False
 record=block.block_record
 if record.has_xdata('AcDbBlockRepBTag'):
  master=next((tag.value for tag in record.get_xdata('AcDbBlockRepBTag') if tag.code==1005),None)
  record=doc.entitydb.get(master) if master else record
 if record is None or not record.has_extension_dict:return False
 graph=record.extension_dict.dictionary.get('ACAD_ENHANCEDBLOCK')
 if graph is None or graph.dxftype()!='ACAD_EVALUATION_GRAPH':return False
 for subclass in graph.xtags.subclasses:
  for tag in subclass:
   if tag.code!=360:continue
   node=doc.entitydb.get(tag.value)
   if node is not None and node.dxftype()=='BLOCKVISIBILITYPARAMETER':return True
 return False

def prepared_device_block(source:bytes,name:str):
 # Wrapping an existing dynamic reference in an outer static block hides its grip.
 # Preserve the supplier's entire reference, native visibility graph and attributes.
 if b'BLOCKVISIBILITYPARAMETER' in source:
  doc=ezdxf.read(io.StringIO(source.decode('utf-8-sig'),newline=None))
  if native_visibility_insert(doc):return source
 if MANIFEST.is_file():
  stat=MANIFEST.stat();row=_prepared_exports((stat.st_mtime_ns,stat.st_size)).get(hashlib.sha256(source).hexdigest())
  if row:
   path=(ROOT/row['export_path']).resolve()
   if path.is_relative_to(ROOT.resolve()) and path.is_file():
    result=path.read_bytes()
    if hashlib.sha256(result).hexdigest()==row['export_sha256']:return result
 return single_device_block(source,name)

def single_device_block(source:bytes,name:str):
 doc=ezdxf.read(io.StringIO(source.decode('utf-8-sig'),newline=None));space=doc.modelspace()
 if native_visibility_insert(doc):return source
 safe=re.sub(r'[^A-Za-z0-9_-]','_',name)[:100] or 'DEVICE'
 while safe in doc.blocks:safe+='_'
 block=doc.blocks.new(safe)
 for entity in list(space):space.move_to_layout(entity,block)
 space.add_blockref(safe,(0,0,0))
 target=io.StringIO();doc.write(target)
 return target.getvalue().encode('utf8')

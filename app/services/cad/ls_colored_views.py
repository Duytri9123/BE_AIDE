"""Style an export copy; keep native geometry, units and explicit source colours."""
import io,re
from functools import lru_cache
import ezdxf

NEUTRAL_ACI={7,8,9,*range(250,256)}

def _neutral_rgb(value):
 channels=((value>>16)&255,(value>>8)&255,value&255)
 return max(channels)-min(channels)<=3

def _neutral_entity(entity,doc,root_handles):
 if entity.dxf.hasattr('true_color'):return _neutral_rgb(entity.dxf.true_color)
 color=entity.dxf.get('color',256)
 if color==0:return entity.dxf.handle in root_handles
 if color!=256:return color in NEUTRAL_ACI
 layer=doc.layers.get(entity.dxf.layer)
 if layer.dxf.hasattr('true_color'):return _neutral_rgb(layer.dxf.true_color)
 return abs(layer.color) in NEUTRAL_ACI

def color_svg_preview(source:bytes):
 # Stored previews already have validated geometry; recolour instead of rebuilding HLR.
 return re.sub(rb'(?i)#(?:ffffff|fff)(?![0-9a-f])',b'#40d9ff',source)

def clear_svg_preview(source:bytes):
 # Presentation-only stroke width. Path coordinates, source colours and DXF stay intact.
 return re.sub(rb'stroke-width:\s*[0-9.]+(?:px)?\s*;',b'stroke-width: 1.1px; vector-effect: non-scaling-stroke;',source)

@lru_cache(maxsize=16)
def colored_dxf(source:bytes):
 doc=ezdxf.read(io.StringIO(source.decode('utf-8-sig',errors='strict'),newline=None))
 roots={e.dxf.handle for e in doc.modelspace()}
 changes={}
 for block in doc.blocks:
  for entity in block:
   # Keep filled faces and existing coloured accents. ByBlock children inherit
   # their insert's colour, including the supplier's native coloured inserts.
   if entity.dxftype() in {'HATCH','SOLID','TRACE','3DFACE','VIEWPORT'}:continue
   if _neutral_entity(entity,doc,roots):
    changes[entity.dxf.handle]=({'CIRCLE':0xFFBF69,'ARC':0xFFBF69,
                           'TEXT':0x7DF5B7,'MTEXT':0x7DF5B7,'ATTRIB':0x7DF5B7,
                           'ATTDEF':0x7DF5B7}.get(entity.dxftype(),0x40D9FF))
  # Attributes are attached to their INSERT, not members of the block layout.
  for insert in block.query('INSERT'):
   for attribute in insert.attribs:
    if _neutral_entity(attribute,doc,roots):changes[attribute.dxf.handle]=0x7DF5B7
 # Do not round-trip native enhanced-block objects through an external writer.
 # Patch only group 420 in the existing graphic entity records; every control
 # object, handle, visibility state, coordinate and original ACI stays untouched.
 lines=source.decode('utf-8-sig').splitlines(keepends=True)
 newline='\r\n' if b'\r\n' in source else '\n'
 starts=[i for i in range(0,len(lines)-1,2) if lines[i].strip()=='0']+[len(lines)]
 output=lines[:starts[0]] if starts else lines[:]
 for start,end in zip(starts,starts[1:]):
  record=lines[start:end];handle=next((record[i+1].strip() for i in range(0,len(record)-1,2) if record[i].strip()=='5'),None)
  rgb=changes.get(handle)
  if rgb is not None:
   existing=next((i for i in range(0,len(record)-1,2) if record[i].strip()=='420'),None)
   if existing is not None:record[existing+1]=str(rgb)+newline
   else:
    base=next((i for i in range(0,len(record)-1,2) if record[i].strip()=='100' and record[i+1].strip()=='AcDbEntity'),None)
    if base is None:raise ValueError('Colour export requires an AcDbEntity subclass')
    insert=next((i for i in range(base+2,len(record)-1,2) if record[i].strip()=='100'),len(record))
    record[insert:insert]=['420'+newline,str(rgb)+newline]
  output.extend(record)
 return (b'\xef\xbb\xbf' if source.startswith(b'\xef\xbb\xbf') else b'')+''.join(output).encode('utf8')

@lru_cache(maxsize=16)
def colored_svg(source:bytes):
 from ezdxf.addons.drawing import Frontend,RenderContext,svg,layout
 doc=ezdxf.read(io.StringIO(colored_dxf(source).decode('utf8'),newline=None))
 backend=svg.SVGBackend();Frontend(RenderContext(doc),backend).draw_layout(doc.modelspace(),finalize=True)
 return clear_svg_preview(backend.get_string(layout.Page(0,0,layout.Units.mm)).encode('utf8'))

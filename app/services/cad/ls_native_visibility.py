"""Assemble native visibility states from one reviewed LS or CHINT CAD variant.

The template supplies AutoCAD control objects only. All its original geometry is
removed; actual faces are imported without changing their coordinates or styling.
"""
import io,re,uuid
from functools import lru_cache
from pathlib import Path
import ezdxf
from ezdxf.addons import Importer
from ezdxf.lldxf.types import DXFTag,DXFVertex
from ezdxf.lldxf.tags import Tags

TEMPLATE=Path(__file__).resolve().parents[3]/'scripts/resources/ls_visibility_template.dxf'

def visibility_document(faces, identity, active, brand='LS'):
    """faces: ordered (unique state name, original DXF bytes) of ONE variant."""
    names=[name for name,source in faces]
    if len(names)<2 or len(set(names))!=len(names) or active not in names:
        raise ValueError('A visibility set needs unique, real faces and a valid active face')
    doc=ezdxf.readfile(TEMPLATE)
    oldref=list(doc.modelspace())[0]
    record=doc.blocks[oldref.dxf.name].block_record
    record=doc.entitydb[next(t.value for t in record.get_xdata('AcDbBlockRepBTag') if t.code==1005)]
    master=doc.blocks[record.dxf.name]
    graph=record.extension_dict.dictionary['ACAD_ENHANCEDBLOCK']
    nodes=[doc.entitydb[t.value] for sub in graph.xtags.subclasses for t in sub if t.code==360]
    parameter=next(n for n in nodes if n.dxftype()=='BLOCKVISIBILITYPARAMETER')
    doc.modelspace().delete_all_entities();master.delete_all_entities()
    safe=re.sub(r'[^A-Z0-9]','',brand.upper())+'_'+uuid.uuid5(uuid.NAMESPACE_URL,identity).hex
    doc.blocks.rename_block(master.name,safe);master=doc.blocks[safe]
    for block in list(doc.blocks):
        if not block.name.startswith(('*Model','*Paper')) and block.name not in (safe,'_ArchTick'):
            doc.blocks.delete_block(block.name,safe=False)
    if 'ACAD_SORTENTS' in record.extension_dict.dictionary:
        del record.extension_dict.dictionary['ACAD_SORTENTS']
    for key in ('AcDbDynamicBlockGUID','AcDbDynamicBlockTrueName'):
        if record.has_xdata(key):record.discard_xdata(key)
    if 'AcDbDynamicBlockGUID' not in doc.appids:doc.appids.new('AcDbDynamicBlockGUID')
    record.set_xdata('AcDbDynamicBlockGUID',[(1000,str(uuid.uuid5(uuid.NAMESPACE_DNS,identity)).upper())])
    states=[]
    # Native inserts start with the first visibility state. Match its hidden flags.
    faces=sorted(faces,key=lambda x:x[0]!=active)
    for index,(name,source) in enumerate(faces):
        original=ezdxf.read(io.StringIO(source.decode('utf-8-sig'),newline=None))
        if original.units!=4 or not len(original.modelspace()) or original.audit().errors:
            raise ValueError('Invalid or non-mm face: '+name)
        block=doc.blocks.new(safe+'_FACE_'+str(index))
        importer=Importer(original,doc)
        importer.import_entities(original.modelspace(),target_layout=block);importer.finalize()
        ref=master.add_blockref(block.name,(0,0,0));ref.dxf.invisible=int(name!=active)
        states.append((name,ref.dxf.handle))
    parameter.xtags.subclasses[-1]=Tags([
        DXFTag(100,'AcDbBlockVisibilityParameter'),DXFTag(281,1),
        DXFTag(301,'CAD_FACE'),DXFTag(302,'Faces of this '+brand+' CAD variant'),DXFTag(91,0),
        DXFTag(93,len(states)),*[DXFTag(331,h) for _,h in states],DXFTag(92,len(states)),
        *[t for name,h in states for t in (DXFTag(303,name),DXFTag(94,1),DXFTag(332,h),DXFTag(95,0))]])
    for node in nodes:
        for sub in node.xtags.subclasses:
            for i,tag in enumerate(sub):
                if tag.code==1010:sub[i]=DXFVertex(1010,(-5,-5,0))
    from .layer_resource_links import repair_invalid_layer_resources
    repair_invalid_layer_resources(doc)
    doc.units=4;doc.header['$INSUNITS']=4
    doc.modelspace().add_blockref(safe,(0,0,0))
    assert not doc.audit().errors
    return doc

def visibility_dxf(faces,identity,active,brand='LS'):
    doc=visibility_document(faces,identity,active,brand);out=io.StringIO();doc.write(out)
    return out.getvalue().encode('utf8')

@lru_cache(maxsize=4)
def _cached_visibility(faces,identity,active,template_revision,brand='LS'):
    return visibility_dxf(faces,identity,active,brand)

def device_visibility_dxf(device,view_id,read_source):
    """Only combine available faces of the selected variant and engraved model."""
    from .ls_view_coverage import is_ls,view_role
    from ..catalog_view_health import displayable
    from ..catalog_view_models import view_models
    from ..customer_equipment_information import public_view_id
    brand='LS' if is_ls(device.get('brand')) else 'CHINT' if str(device.get('brand') or '').upper()=='CHINT' else None
    if not brand:return None
    selected=next((v for v in device.get('views',[]) if view_id in (v['id'],public_view_id(v['id']))),None)
    if not selected:return None
    variant=selected.get('cad_variant_id') or device['id']
    candidates=[v for v in device['views'] if (v.get('cad_variant_id') or device['id'])==variant and displayable(v)]
    if brand=='CHINT':
        # Legacy partial references have not established all matching views.
        # Keep their source projection downloadable; never invent a full set.
        from .ls_view_coverage import view_coverage
        if not view_coverage(candidates)['complete']:return None
    models=set(view_models(device,selected))
    if len({tuple(view_models(device,v)) for v in candidates})>1:
        # A shared side view does not identify which engraved model to export.
        if len(models)!=1:return None
        candidates=[v for v in candidates if not view_models(device,v) or set(view_models(device,v))==models]
    labels={'front':'FRONT','rear':'REAR','left':'SIDE-L','right':'SIDE','top':'TOP','bottom':'BOTTOM'}
    def state(v):
        if str(v.get('label') or '').startswith('Nắp che mặt trước'):return 'COVER'
        return labels.get(view_role(v)) or {
            'Mặt bên':'SIDE','SIDE':'SIDE','Nắp che mặt trước':'COVER',
            'Mặt bên · kèm đầu nối':'SIDE-CONNECTING',
            'Mặt xuyên dây':'FRONT-OPENING','Mặt đế gá theo bản vẽ':'MOUNTING',
        }.get(v.get('face') or v.get('label'))
    states=[state(v) for v in candidates]
    duplicates={name for name in states if states.count(name)>1}
    if duplicates:
        # Keep explicitly numbered source alternatives distinct; do not guess a role.
        states=[label+'-'+m.group(1) if label in duplicates and
                (m:=re.search(r' · bản (\d+)$',str(v.get('label') or ''))) else label
                for label,v in zip(states,candidates)]
    if len(states)<2 or None in states or len(set(states))!=len(states):return None
    faces=tuple((label,read_source(v['id'])) for label,v in zip(states,candidates))
    active=states[next(i for i,v in enumerate(candidates) if v['id']==selected['id'])]
    # Include source content and the entire variant/model identity in the cache key.
    identity=device['id']+':'+variant+':'+','.join(sorted(models))
    stat=TEMPLATE.stat()
    return _cached_visibility(faces,identity,active,(stat.st_mtime_ns,stat.st_size),brand)

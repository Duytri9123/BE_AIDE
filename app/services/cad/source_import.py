"""Namespace supplier text styles so target defaults cannot replace their fonts."""
import hashlib
from ezdxf.addons import Importer


def import_source_entities(source, destination, entities, target_layout, identity):
    prefix = 'SRC_' + hashlib.sha256(str(identity).encode()).hexdigest()[:12] + '_'
    styles = {}
    for entry in list(source.styles):
        name = entry.dxf.name
        replacement = prefix + name
        if replacement not in source.styles:
            source.styles.duplicate_entry(name, replacement)
        styles[name] = replacement
    # Mutate the in-memory import document, never the supplier file.
    for entity in list(source.entitydb.values()):
        if entity.is_alive and entity.dxftype() in ('TEXT', 'MTEXT', 'ATTRIB', 'ATTDEF'):
            style = entity.dxf.get('style', 'Standard')
            if style in styles:
                entity.dxf.style = styles[style]
    importer = Importer(source, destination)
    importer.import_entities(entities, target_layout=target_layout)
    importer.finalize()

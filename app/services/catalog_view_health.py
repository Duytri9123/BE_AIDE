"""Do not publish unresolved or structurally invalid equipment projections."""
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree
import hashlib, json

QUARANTINE = Path(__file__).resolve().parents[1]/'data/catalog_quarantined_views.json'
VERIFIED = Path(__file__).resolve().parents[1]/'data/catalog_verified_view_health.json'
CATALOG = Path(__file__).resolve().parents[2]/'data/CatalogTB'
VIEW_INDEX = Path(__file__).resolve().parents[1]/'data/catalog_customer_cad_measurements.json'

@lru_cache(maxsize=2)
def _view_index(revision):
    return json.loads(VIEW_INDEX.read_text(encoding='utf8')).get('views',{})

def current_view_displayable(catalog_id,view_id):
    """Recheck saved display snapshots against the current, reviewed file."""
    if not VIEW_INDEX.is_file():return True
    stat=VIEW_INDEX.stat();row=_view_index((stat.st_mtime_ns,stat.st_size)).get(f'{catalog_id}:{view_id}')
    if not row:return True  # New imports are validated by the source builder.
    try:
        path=(CATALOG/row['path']).resolve();preview=path.with_name('xem_truoc.svg')
        if not path.is_relative_to(CATALOG.resolve()):return False
        stat=path.stat();ps=preview.stat()
        return _valid(str(path),(stat.st_mtime_ns,stat.st_size),str(preview),(ps.st_mtime_ns,ps.st_size))
    except Exception:return False

@lru_cache(maxsize=2)
def _verified(revision):
    return json.loads(VERIFIED.read_text(encoding='utf8')).get('files',{})

@lru_cache(maxsize=2)
def _quarantined(revision):
    return json.loads(QUARANTINE.read_text(encoding='utf8')).get('items',[])

def quarantined(catalog_id, view_id):
    if not QUARANTINE.is_file(): return False
    stat=QUARANTINE.stat()
    return any(row['catalog_id']==catalog_id and view_id in {row['view_id'],'v-'+hashlib.sha256(row['view_id'].encode()).hexdigest()[:20]}
               for row in _quarantined((stat.st_mtime_ns,stat.st_size)))

def targeted(brand):
    return str(brand or '').strip().upper() in {'ABB','LS','LS ELECTRIC','CHINT','SCHNEIDER','SCHNEIDER ELECTRIC','INVT','MITSUBISHI','MITSUBISHI ELECTRIC'}

def displayable(view):
    from .cad.catalogtb_assets import face_code
    label = view.get('face') or view.get('huong_nhin') or view.get('state') or view.get('label') or view.get('name')
    review = view.get('linework_review') or view.get('kiem_tra_net_cad') or {}
    return (not view.get('hidden') and view.get('available') is not False
            and face_code(label) != 'unknown'
            and review.get('status') not in {'unresolved_visible_geometry_defect','invalid_geometry','rejected'})

@lru_cache(maxsize=4096)
def _valid(path, revision, preview, preview_revision):
    import ezdxf
    try:
        if VERIFIED.is_file():
            stat=VERIFIED.stat()
            relative=Path(path).relative_to(CATALOG.resolve()).as_posix() if Path(path).is_relative_to(CATALOG.resolve()) else None
            row=_verified((stat.st_mtime_ns,stat.st_size)).get(relative)
            if row:
                return (hashlib.sha256(Path(path).read_bytes()).hexdigest()==row['sha256']
                        and hashlib.sha256(Path(preview).read_bytes()).hexdigest()==row['preview_sha256'])
        doc = ezdxf.readfile(path)
        audit = doc.audit()
        if doc.units != 4 or not len(doc.modelspace()) or audit.errors or audit.fixes:
            return False
        ElementTree.parse(preview)
        return True
    except Exception:
        return False

def source_displayable(entry, profile_path):
    if not displayable(entry): return False
    from .cad.catalogtb_assets import normalized_source
    try:
        source = (Path(profile_path).parent / entry['duong_dan']).resolve()
        if not source.is_relative_to(Path(profile_path).parent.resolve()): return False
        path = normalized_source(source); preview = source.with_name('xem_truoc.svg')
        stat = path.stat(); ps = preview.stat()
        return _valid(str(path),(stat.st_mtime_ns,stat.st_size),str(preview),(ps.st_mtime_ns,ps.st_size))
    except Exception:
        return False

def asset_displayable(relative):
    """Check current bytes as well as metadata when serving an old asset URL."""
    from .equipment_library import _catalogtb_asset
    from .cad.catalogtb_assets import normalized_source
    try:
        source=_catalogtb_asset(relative)
        if source is None:return False
        drawing=normalized_source(source.with_name('ban_ve.dxf'));preview=source.with_name('xem_truoc.svg')
        stat=drawing.stat();ps=preview.stat()
        return _valid(str(drawing),(stat.st_mtime_ns,stat.st_size),str(preview),(ps.st_mtime_ns,ps.st_size))
    except Exception:return False

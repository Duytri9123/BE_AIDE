"""Rebuild project positions using recovered CatalogTB views, retaining source mechanics."""
from pathlib import Path
import json
import re
import sys
import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext, svg, layout
from ezdxf.addons.drawing.recorder import Recorder
from ezdxf.math import Vec2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'BE_AIDE'))
from app.services.cad.catalogtb_assets import assets
from app.services.cad.library_assets import insert_library_asset
from import_sample_device_faces import recorded, compare_visible


def run():
    out = ROOT / 'outputs/sample-cad-recovery/457'
    source = ezdxf.readfile(out / 'source.dxf')
    drawing = ezdxf.readfile(out / 'source.dxf')
    rows = json.loads((ROOT / 'outputs/order-447-457-audit/cad-face-occurrences.json').read_text(encoding='utf8'))
    catalog = assets(refresh=True)
    replacements = []
    names = {'TIMER 24H CHINT': 'Timer24h', 'CHUYEN MACH': 'Selector',
             '125SRQ': 'Relay125SRQ', 'VTPK_S8FS-C05024J': 'SupplyS8FS'}
    for row in rows:
        if row['order'] != '457' or not row['owner_face']:
            continue
        key = names.get(row['effective_name'])
        state = ' '.join(str(v) for v in row['properties'].values()).upper()
        if row['effective_name'] == 'BKN-LS':
            match = re.search(r'\b([1-3])P', state)
            # Shared SIDE is retained intact; source projection does not identify poles.
            if not match:
                continue
            key = 'BKN_' + match[1] + 'P'
        if not key:
            continue
        face = 'cover' if 'COVER' in state else 'side' if 'SIDE' in state else 'front'
        found = [a for a in catalog if a['profile_path'].startswith(f'ProjectSamples/{key}/') and a['face'] == face]
        if len(found) != 1:
            raise ValueError(f'Source view unresolved: {key}/{face}')
        original = source.entitydb.get(row['handle'])
        before = recorded(source, [original])
        box = before.bbox()
        m = drawing.modelspace()
        count_before = len(m)
        insert_library_asset(m, found[0]['id'], box.extmin.x, box.extmin.y)
        inserted = list(m)[-1]
        for attribute in ('layer', 'color', 'true_color', 'lineweight', 'linetype', 'ltscale'):
            if original.dxf.hasattr(attribute):
                setattr(inserted.dxf, attribute, original.dxf.get(attribute))
        try:
            maximum = compare_visible(before, recorded(drawing, [inserted]))
        except ValueError as exc:
            raise ValueError(f"{key}/{face}, handle {row['handle']}: {exc}") from exc
        old = drawing.entitydb.get(row['handle'])
        if old is None:
            raise ValueError('Source handle missing during reconstruction')
        m.delete_entity(old)
        if len(m) != count_before:
            raise ValueError('Reconstruction duplicated a projection')
        replacements.append({'source_handle': row['handle'], 'asset_id': found[0]['id'],
                             'panel': row['panel'], 'source_face': row['owner_face'],
                             'cad_face': face, 'maximum_curve_deviation_mm': maximum})
    drawing.saveas(out / 'layout-redrawn-from-catalog.dxf')
    counts = {p: sum(r['panel'] == p and r['source_face'] in ('mounting_plate', 'inner_door')
                    for r in replacements) for p in ('PX1', 'PX2')}
    result = {'status': 'source_geometry_review', 'source_order': '457',
              'replaced_projections': len(replacements), 'replacements': replacements,
              'remaining_model_checks': ['BKN source geometry versus LA63H/LA63N quotation model',
                                          'Exploded contactor slots versus NCH8-20 2P exact geometry',
                                          'Selector front/side mounting alignment',
                                          'Wall mounting quotation versus source plinth'],
              'fabrication_ready': False, 'physical_replacements_by_panel': counts,
              'original_mechanical_geometry_retained': True}
    (out / 'redraw-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    recorder = Recorder()
    Frontend(RenderContext(drawing), recorder).draw_layout(drawing.modelspace(), finalize=True)
    for panel, bounds in [('PX1', (-98300, 11650, -94200, 13200)),
                          ('PX2', (-98400, 8450, -94200, 10050))]:
        player = recorder.player().copy()
        player.crop_rect(Vec2(bounds[:2]), Vec2(bounds[2:]), .01)
        backend = svg.SVGBackend()
        player.replay(backend)
        (out / (panel.lower() + '-redrawn.svg')).write_text(backend.get_string(layout.Page(0, 0)), encoding='utf8')
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
        figure = plt.figure(figsize=(16, 6))
        axes = figure.add_axes([.01, .01, .98, .98])
        raster = MatplotlibBackend(axes)
        player.replay(raster)
        raster.finalize()
        axes.set_aspect('equal', adjustable='box')
        figure.savefig(out / (panel.lower() + '-redrawn.png'), dpi=160, facecolor='#212830')
        plt.close(figure)
    print(json.dumps({'replaced_projections': len(replacements), 'physical_replacements_by_panel': counts,
                      'all_checked_views_match_source': True, 'fabrication_ready': False}))


if __name__ == '__main__':
    run()

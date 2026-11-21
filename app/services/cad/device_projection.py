"""Visible, labelled orthographic device geometry for approximate 3D previews.

Use the drawing pipeline, not recursive_decompose/bbox: dynamic blocks contain
invisible alternative states that must never inflate the selected projection.
"""
import hashlib
from pathlib import Path

import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.recorder import (
    Recorder, PointsRecord, SolidLinesRecord, PathRecord, FilledPathsRecord,
)

from .catalogtb_assets import insertion_source


def visible_projection(source: Path, root: Path):
    path = insertion_source(source)
    drawing = ezdxf.readfile(path)
    if drawing.units != 4:
        raise ValueError('Mặt CAD chưa xác nhận đơn vị mm.')
    result = visible_entity_projection(drawing, drawing.modelspace())
    return {**result, 'source': path.relative_to(root.resolve()).as_posix(),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def visible_entity_projection(drawing, entities):
    """Retain the active dynamic state and transformed coordinates of an INSERT."""
    recorder = Recorder()
    Frontend(RenderContext(drawing), recorder).draw_entities(entities)
    player = recorder.player()
    bounds = player.bbox()
    if not bounds.has_data:
        raise ValueError('Mặt CAD không có hình học hiển thị.')
    x0, y0 = bounds.extmin
    paths = []

    def add(points):
        points = [[round(p.x - x0, 5), round(p.y - y0, 5)] for p in points]
        if len(points) > 1:
            paths.append(points)

    def curve(path):
        for sub in path.to_path().sub_paths():
            add(sub.flattening(.1, segments=8))

    for record, _ in player.recordings():
        if isinstance(record, PointsRecord):
            add(record.points.vertices())
        elif isinstance(record, SolidLinesRecord):
            points = list(record.lines.vertices())
            for i in range(0, len(points), 2):
                add(points[i:i + 2])
        elif isinstance(record, PathRecord):
            curve(record.path)
        elif isinstance(record, FilledPathsRecord):
            for path_data in record.paths:
                curve(path_data)
    return dict(paths=paths, width=round(bounds.size.x, 5), height=round(bounds.size.y, 5),
                origin_mm=[x0, y0], units='mm', visibility='selected_visible_state')

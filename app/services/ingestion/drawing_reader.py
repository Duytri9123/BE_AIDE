"""Source-grounded PDF and image context shared by chat and drawing extraction."""
from __future__ import annotations

from functools import lru_cache
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[3]
_OCR_LOCK = threading.Lock()


def ocr_python():
    override = os.environ.get('DRAWING_OCR_PYTHON')
    if override:
        return Path(override)
    return ROOT / '.venv-ocr' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


@lru_cache(maxsize=32)
def _ocr_cached(path, mtime_ns, size, language):
    python = ocr_python()
    if not python.is_file():
        raise RuntimeError('OCR runtime missing; run scripts/install_drawing_ocr.ps1')
    with _OCR_LOCK, tempfile.TemporaryDirectory(prefix='aide_ocr_') as folder:
        output = Path(folder) / 'result.json'
        request = {'path': path, 'language': language, 'output': str(output)}
        with subprocess.Popen(
                [str(python), str(ROOT / 'scripts/drawing_ocr_worker.py')],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                encoding='utf-8', errors='replace', cwd=str(ROOT),
                env={**os.environ, 'PYTHONUTF8': '1'},
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        ) as process:
            try:
                _, stderr = process.communicate(json.dumps(request), timeout=300)
            except subprocess.TimeoutExpired as exc:
                # Windows venv launchers can create a child interpreter. Stop
                # that process tree too so timed-out OCR does not keep running.
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                   capture_output=True, timeout=15,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    process.kill()
                process.communicate(timeout=15)
                raise RuntimeError('PaddleOCR timed out after 300 seconds; source requires visual review') from exc
            returncode = process.returncode
        if not output.is_file():
            raise RuntimeError('PaddleOCR process failed: ' + stderr[-800:])
        payload = json.loads(output.read_text(encoding='utf-8'))
        if returncode or payload.get('error'):
            raise RuntimeError(payload.get('error') or 'PaddleOCR process failed')
        return payload


def read_image(path):
    path = Path(path).resolve()
    stat = path.stat()
    # Return a fresh value so callers cannot mutate cached evidence.
    return json.loads(json.dumps(_ocr_cached(str(path), stat.st_mtime_ns, stat.st_size,
                                          os.environ.get('DRAWING_OCR_LANGUAGE', 'vi'))))


def read_pdf_page(path, page_number, include_ocr=False):
    import pymupdf
    with pymupdf.open(str(path)) as document:
        if not 1 <= page_number <= len(document):
            raise ValueError('PDF page out of range')
        page = document[page_number - 1]
        words = []
        for x0, y0, x1, y1, text, *_ in page.get_text('words', sort=True):
            rect = pymupdf.Rect(x0, y0, x1, y1) * page.rotation_matrix
            words.append({'text': text, 'box_2d': [round(rect.y0 / page.rect.height * 1000),
                round(rect.x0 / page.rect.width * 1000), round(rect.y1 / page.rect.height * 1000),
                round(rect.x1 / page.rect.width * 1000)]})
        paths = page.get_drawings()
        vectors = []
        for path in paths[:256]:
            rect = path['rect'] * page.rotation_matrix
            segments = []
            for item in path['items'][:32]:
                values = []
                for value in item[1:]:
                    if isinstance(value, pymupdf.Point):
                        point = value * page.rotation_matrix
                        values.append([point.x, point.y])
                    elif isinstance(value, pymupdf.Rect):
                        values.append(list(value * page.rotation_matrix))
                    elif isinstance(value, pymupdf.Quad):
                        values.append([[p.x, p.y] for p in (value * page.rotation_matrix)])
                    else:
                        values.append(value)
                segments.append([item[0], *values])
            vectors.append({'rect': list(rect), 'items': segments, 'width': path.get('width'),
                            'items_truncated': len(path['items']) > 32})
        result = {'engine': 'pymupdf', 'page': page_number, 'page_count': len(document),
                  'text': page.get_text(sort=True), 'words': words,
                  'vector_path_count': len(paths),
                  'vector_paths': vectors, 'vector_paths_truncated': len(paths) > 256,
                  'vector_units': 'PDF points on rotated page, not physical CAD dimensions',
                  'coordinate_system': 'box_2d=[top,left,bottom,right], 0..1000, rotated page',
                  'needs_visual_verification': True}
        if include_ocr:
            # OCR coordinates use this same rotated page canvas.
            scale = min(3.0, 6000 / max(page.rect.width, page.rect.height))
            with tempfile.TemporaryDirectory(prefix='aide_pdf_ocr_') as folder:
                image = Path(folder) / 'page.png'
                page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False).save(str(image))
                result['ocr'] = read_image(image)
                result['ocr']['page'] = page_number
        return result


def evidence_context(evidence, max_chars=12000):
    """Bound JSON without cutting it in the middle of a coordinate or label."""
    rows = evidence.get('rows', evidence.get('words', []))
    header = {k: v for k, v in evidence.items() if k not in {'rows', 'words', 'text', 'ocr', 'vector_paths'}}
    selected = []
    for row in rows:
        candidate = {**header, 'rows': [*selected, row], 'truncated': True}
        if len(json.dumps(candidate, ensure_ascii=False)) > max_chars:
            break
        selected.append(row)
    return json.dumps({**header, 'rows': selected, 'truncated': len(selected) < len(rows)}, ensure_ascii=False)

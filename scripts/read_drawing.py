"""CLI for agents: read one PDF page or an image into source-attributed JSON."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.ingestion.drawing_reader import read_image, read_pdf_page


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--page', type=int, default=1, help='PDF page, 1-based')
    parser.add_argument('--ocr', action='store_true', help='Also OCR the rendered PDF page')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = (read_pdf_page(args.path, args.page, include_ocr=args.ocr)
              if args.path.suffix.lower() == '.pdf' else read_image(args.path))
    result['source_file'] = str(args.path.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(args.output.resolve()), 'engine': result['engine'],
                      'rows': len(result.get('rows', result.get('words', []))) }))


if __name__ == '__main__':
    main()

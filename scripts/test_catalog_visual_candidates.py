import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from app.services.catalog_visual_candidates import matching_view


class VisualEvidenceTests(unittest.TestCase):
    def test_both_source_drawing_and_preview_must_match(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);drawing=root/'view.dxf';preview=root/'xem_truoc.svg'
            drawing.write_bytes(b'original drawing');preview.write_bytes(b'original preview')
            (root/'profile.json').write_text(json.dumps({'cad_don':[{'id_hinh_goc':'v','duong_dan':'view.dxf'}]}),encoding='utf8')
            dxf=hashlib.sha256(drawing.read_bytes()).hexdigest();svg=hashlib.sha256(preview.read_bytes()).hexdigest()
            self.assertIsNotNone(matching_view(root,'profile.json','v',dxf,svg))
            preview.write_bytes(b'different preview')
            self.assertIsNone(matching_view(root,'profile.json','v',dxf,svg))
            preview.write_bytes(b'original preview');drawing.write_bytes(b'different drawing')
            self.assertIsNone(matching_view(root,'profile.json','v',dxf,svg))
            self.assertIsNone(matching_view(root,'../profile.json','v',dxf,svg))


if __name__=='__main__':unittest.main()

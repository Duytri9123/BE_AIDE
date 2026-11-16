import tempfile
import unittest
from pathlib import Path
import ezdxf
from app.services.ingestion.cad_source_evidence import cad_evidence, region_normalized


class CadSourceScopeTests(unittest.TestCase):
    def test_overview_includes_distant_panels_and_separate_rating_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'panels.dxf'
            doc = ezdxf.new()
            msp = doc.modelspace()
            for text, point in [('MCB', (0, 0)), ('6A', (20, 0)),
                                ('MCCB-3P-150A', (0, 1000)), ('PANEL-B', (40, 1000))]:
                msp.add_text(text, dxfattribs={'insert': point, 'height': 2})
            doc.saveas(path)
            overview = cad_evidence(path)
            self.assertEqual(len(overview['labels']), 4)
            self.assertEqual({r['text'] for r in overview['labels']}, {'MCB', '6A', 'MCCB-3P-150A', 'PANEL-B'})
            region = region_normalized(overview['bounds'], [-20, -20, 100, 20])
            zoom = cad_evidence(path, region)
            self.assertEqual({r['text'] for r in zoom['labels']}, {'MCB', '6A'})
            for row in zoom['labels']:
                self.assertTrue(zoom['view_bounds'][1] <= row['y'] <= zoom['view_bounds'][3])


if __name__ == '__main__':
    unittest.main()

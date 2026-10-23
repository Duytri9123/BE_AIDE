import tempfile
import unittest
from pathlib import Path
import ezdxf
from PIL import Image
from app.services.ingestion.cad_visual_source import render_schematic_source


class CadVisualSourceTests(unittest.TestCase):
    def test_actual_schematic_layer_renders_with_nearby_instruments_and_is_cached(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.dxf';drawing=ezdxf.new();drawing.layers.new('SLD')
            model=drawing.modelspace()
            model.add_line((0,0),(100,100),dxfattribs={'layer':'SLD'})
            model.add_text('MCCB',dxfattribs={'insert':(20,40),'layer':'SLD','height':5})
            model.add_circle((50,50),3)
            model.add_text('V',dxfattribs={'insert':(49,49),'height':2})
            model.add_text('UNRELATED FLOOR PLAN',dxfattribs={'insert':(10000,10000),'height':100})
            drawing.saveas(path)
            image=Path(render_schematic_source(str(path)))
            self.assertTrue(image.is_file())
            with Image.open(image) as opened:
                self.assertGreater(opened.width,500)
                self.assertGreater(opened.height,500)
            stamp=image.stat().st_mtime_ns
            self.assertEqual(render_schematic_source(str(path)),str(image))
            self.assertEqual(image.stat().st_mtime_ns,stamp)

    def test_unidentified_layers_do_not_claim_an_automatic_schematic_crop(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.dxf';ezdxf.new().saveas(path)
            self.assertIsNone(render_schematic_source(str(path)))


if __name__=='__main__':unittest.main()

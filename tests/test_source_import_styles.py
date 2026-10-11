import unittest
import ezdxf
from app.services.cad.source_import import import_source_entities


class SourceStyleTests(unittest.TestCase):
    def test_supplier_standard_font_does_not_become_target_default(self):
        source, target = ezdxf.new(), ezdxf.new()
        source.styles.get('Standard').dxf.font = 'arial.ttf'
        target.styles.get('Standard').dxf.font = 'times.ttf'
        source.modelspace().add_text('Timer 24h', dxfattribs={'style': 'Standard'})
        import_source_entities(source, target, source.modelspace(), target.modelspace(), 'timer')
        text = list(target.modelspace())[0]
        self.assertNotEqual(text.dxf.style, 'Standard')
        self.assertEqual(target.styles.get(text.dxf.style).dxf.font, 'arial.ttf')
        self.assertEqual(target.styles.get('Standard').dxf.font, 'times.ttf')

    def test_nested_block_text_uses_supplier_style(self):
        source, target = ezdxf.new(), ezdxf.new()
        source.styles.get('Standard').dxf.font = 'arial.ttf'
        source.blocks.new('CONTROL').add_text('AUTO')
        source.modelspace().add_blockref('CONTROL', (0, 0))
        import_source_entities(source, target, source.modelspace(), target.modelspace(), 'control')
        text = list(target.blocks['CONTROL'])[0]
        self.assertEqual(target.styles.get(text.dxf.style).dxf.font, 'arial.ttf')

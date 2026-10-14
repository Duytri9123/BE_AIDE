import unittest
import ezdxf
from scripts.audit_library_dxf_identity import drawing_text


class DxfIdentityExtractionTests(unittest.TestCase):
    def test_nested_block_text_and_insert_attributes_are_preserved(self):
        doc=ezdxf.new()
        inner=doc.blocks.new('inner');inner.add_text('IDEC')
        outer=doc.blocks.new('outer');outer.add_blockref('inner',(0,0))
        ref=doc.modelspace().add_blockref('outer',(0,0));ref.add_attrib('MODEL','RT18-32')
        self.assertEqual(list(drawing_text(doc.modelspace(),doc)),['RT18-32','IDEC'])

    def test_repeated_and_cyclic_blocks_do_not_expand_geometry(self):
        doc=ezdxf.new()
        block=doc.blocks.new('loop');block.add_text('DIN310');block.add_blockref('loop',(0,0))
        doc.modelspace().add_blockref('loop',(0,0));doc.modelspace().add_blockref('loop',(10,0))
        self.assertEqual(list(drawing_text(doc.modelspace(),doc)),['DIN310'])


if __name__=='__main__':unittest.main()

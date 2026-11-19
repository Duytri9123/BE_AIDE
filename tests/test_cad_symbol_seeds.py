import tempfile
import unittest
from pathlib import Path
import ezdxf
from app.services.ai.cad_symbol_seeds import seed_named_symbols


class NativeSymbolSeedTests(unittest.TestCase):
    def test_incomer_label_alone_does_not_establish_a_horizontal_schedule(self):
        from app.services.ai.cad_branch_evidence import horizontal_schedule_rows
        evidence={'labels':[{'id':'label','x':10,'y':20,'height':2}],
                  'rows':[{'id':'label','rating_id':'label','tag':''}]}
        self.assertEqual(horizontal_schedule_rows(evidence),[])

    def test_complete_group_uses_native_circles_instead_of_clipped_proposal(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.dxf'
            doc=ezdxf.new()
            block=doc.blocks.new('ICC-DEN BAO PHA');block.add_circle((0,0),2)
            for x in (20,22,24):doc.modelspace().add_blockref(block.name,(x,20))
            doc.saveas(path)
            proposal={'device_id':'0','verified':False,'symbol_box_2d':[780,190,790,210],
                      'text_box_2d':[750,180,770,420]}
            result=seed_named_symbols(path,{'view_bounds':[0,0,100,100],'labels':[]},
                [{'category':'LIGHT','name':'Đèn báo pha','quantity':3,'drawing_quantity':3}], [proposal])[0]
            self.assertEqual(result['symbol_box_2d'],[780,180,820,260])
            self.assertEqual(len(result['source_symbol_handles']),3)
            self.assertNotIn('audit_observed',result)

    def test_unrelated_block_does_not_replace_a_device(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.dxf';doc=ezdxf.new()
            block=doc.blocks.new('OTHER');block.add_circle((0,0),2)
            doc.modelspace().add_blockref(block.name,(20,20));doc.saveas(path)
            proposal={'device_id':'0','symbol_box_2d':[780,190,790,210]}
            result=seed_named_symbols(path,{'view_bounds':[0,0,100,100],'labels':[]},
                [{'category':'MCB','name':'MCB','quantity':1}], [proposal])[0]
            self.assertEqual(result,proposal)

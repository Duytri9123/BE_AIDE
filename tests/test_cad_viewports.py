import unittest
import ezdxf
from app.services.ingestion.cad_viewports import overlapping_entities,schematic_sheet_windows

class CadViewportTests(unittest.TestCase):
    def test_source_frame_includes_schematic_with_title_below_and_deduplicates_title_block(self):
        doc=ezdxf.new();block=doc.blocks.new('sheet')
        block.add_lwpolyline([(0,0),(100,0),(100,60),(0,60)],close=True)
        doc.modelspace().add_blockref('sheet',(200,100))
        labels=[{'text':'SƠ ĐỒ NGUYÊN LÝ TỦ ĐIỆN','x':220,'y':105},
                {'text':'SƠ ĐỒ NGUYÊN LÝ TỦ ĐIỆN','x':290,'y':105},
                {'text':'MCB-3P-25A','x':230,'y':140}]
        self.assertEqual(schematic_sheet_windows(doc,labels,[0,0,1000,1000]),[[.2,.84,.3,.9]])
        labels.append({'text':'SƠ ĐỒ NGUYÊN LÝ','x':500,'y':500})
        self.assertEqual(schematic_sheet_windows(doc,labels,[0,0,1000,1000]),[])

    def test_transformed_nested_block_and_attribute_are_retained(self):
        doc=ezdxf.new();inner=doc.blocks.new('inner');inner.add_line((0,0),(10,20))
        outer=doc.blocks.new('outer');outer.add_blockref('inner',(20,30))
        near=doc.modelspace().add_blockref('outer',(100,100),dxfattribs={'rotation':90,'xscale':-2,'yscale':3})
        far=doc.modelspace().add_blockref('outer',(500,500))
        selected=overlapping_entities(doc,[-100,0,200,200])
        self.assertIn(near,selected);self.assertNotIn(far,selected)
        far.add_attrib('TAG','A',(10,10),dxfattribs={'height':2})
        self.assertIn(far,overlapping_entities(doc,[0,0,20,20]))
        grid=doc.modelspace().add_blockref('inner',(1000,1000),dxfattribs={'column_count':2,'column_spacing':500})
        self.assertIn(grid,overlapping_entities(doc,[1490,990,1520,1040]))

class NativeBranchEvidenceTests(unittest.TestCase):
    def test_rotated_label_and_symbol_produce_source_boxes(self):
        import tempfile
        from pathlib import Path
        from app.services.ai.cad_branch_evidence import seed_vertical_branch_boxes
        doc=ezdxf.new();cb=doc.blocks.new('CB');cb.add_circle((0,0),5);cb.add_line((0,-5),(0,-20))
        space=doc.modelspace();space.add_blockref('CB',(500,800))
        space.add_text('P1. LOAD',dxfattribs={'insert':(500,100),'height':10,'rotation':90})
        for text,y in [('MCB',790),('1P',780),('10A',770),('6KA',760)]:space.add_text(text,dxfattribs={'insert':(460,y),'height':5})
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.dxf';doc.saveas(path)
            boxes=seed_vertical_branch_boxes(path,[0,0,1,1],[{'category':'MCB','tag':'P1','connected_load':'LOAD'}],[])
        self.assertEqual(len(boxes),1)
        self.assertEqual(boxes[0]['geometry_source'],'native_cad_block_and_rotated_text')
        label=boxes[0]['tag_box_2d'];self.assertGreater(label[0],boxes[0]['symbol_box_2d'][2])
        self.assertEqual(label,boxes[0]['load_box_2d'])
        self.assertEqual(boxes[0]['load_label'],'P1. LOAD')

class DiscoveryCoordinateTests(unittest.IsolatedAsyncioTestCase):
    async def test_tile_coordinates_map_back_to_original_drawing(self):
        import json,tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import patch,AsyncMock
        from PIL import Image
        from app.services.ai import takeoff_regions as regions
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'drawing.dwg';path.write_bytes(b'fixture')
            image=Path(folder)/'frame.png';Image.new('RGB',(200,200),'white').save(image)
            file=SimpleNamespace(id=77,filename='drawing.dwg',file_path=str(path))
            class DB:
                async def execute(self,*a,**k):return SimpleNamespace(scalars=lambda:SimpleNamespace(all=lambda:[file]))
            with patch('app.services.ingestion.cad_parser.CadParserService.prepare_analysis_path',return_value='fixture.dxf'), \
                 patch('app.services.ingestion.cad_source_evidence.cad_evidence',return_value={'bounds':[0,0,1000,1000],'discovery_regions':[[.2,.3,.6,.8]]}), \
                 patch('app.services.ingestion.cad_visual_source.render_schematic_source',return_value=str(image)), \
                 patch.object(regions.ConnectionPoolService,'get_ordered_connections',new=AsyncMock(return_value=[object()])), \
                 patch.object(regions.ConnectionPoolService,'call_with_fallback',new=AsyncMock(return_value=(json.dumps({'panels':[{'panel_code':'MDB','source_region':[.1,.2,.9,.8]}]}),None))):
                result=await regions.discover_panels(DB(),99999,[77])
            panel=result['detected_panels'][0]
            for actual,expected in zip(panel['source_region'],[.24,.4,.56,.7]):self.assertAlmostEqual(actual,expected)
            self.assertEqual(panel['source_file_id'],77)

if __name__=='__main__':unittest.main()

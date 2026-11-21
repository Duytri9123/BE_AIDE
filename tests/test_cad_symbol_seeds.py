import tempfile
import unittest
from pathlib import Path
import ezdxf
from app.services.ai.cad_symbol_seeds import seed_named_symbols


class NativeSymbolSeedTests(unittest.TestCase):
    def test_unlabeled_ct_requires_a_winding_connected_to_the_as_circuit(self):
        from app.services.ai.cad_symbol_seeds import unlabeled_ct_cluster
        doc = ezdxf.new()
        modelspace = doc.modelspace()
        upper = modelspace.add_arc((100, 200), 10, 45, 315)
        modelspace.add_arc((100, 186), 10, 45, 315)
        modelspace.add_line((100, 150), (100, 250))
        link = modelspace.add_line(upper.end_point, (145, upper.end_point.y))
        evidence = {'view_bounds': [0, 0, 400, 400],
                    'labels': [{'text': 'AS', 'id': 'selector', 'x': 150, 'y': 189, 'height': 8}]}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'source.dxf'
            doc.saveas(path)
            row = unlabeled_ct_cluster(path, evidence)
            self.assertEqual((row['category'], row['quantity'], row['unit'], row['spec']), ('CT', 1, 'Cụm', ''))
            modelspace.delete_entity(link)
            doc.saveas(path)
            self.assertIsNone(unlabeled_ct_cluster(path, evidence))

    def test_vertical_candidate_uses_an_actual_native_breaker_block_and_printed_heading(self):
        from app.services.ai.cad_branch_evidence import native_vertical_candidates
        doc=ezdxf.new();block=doc.blocks.new('CB');block.add_line((-5,-5),(5,5))
        doc.modelspace().add_blockref('CB',(25,200))
        labels=[{'id':str(i),'text':text,'x':10,'y':205-i*10,'height':5,
                 'bounds':[10,200-i*10,20,205-i*10]} for i,text in enumerate(('RCBO','2P','20A','6kA'))]
        labels.append({'id':'load','text':'P20. THU NGÂN','x':25,'y':50,'height':5,'bounds':[23,0,27,100]})
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'native.dxf';doc.saveas(path)
            result=native_vertical_candidates(path,{'view_bounds':[0,0,1000,1000],'labels':labels})
        self.assertEqual(len(result['devices']),1)
        row=result['devices'][0]
        self.assertEqual((row['tag'],row['category'],row['poles'],row['in_a'],row['icu_ka']),('P20','RCBO',2,20,6))
        self.assertEqual(row['connected_load'],'THU NGÂN')
        self.assertNotIn('symbol_verified',row)
        self.assertTrue(any(i.startswith('cad_entity_') for i in row['source_evidence_ids']))

    def test_native_vertical_join_restores_omitted_branch_and_preserves_distinct_spare(self):
        from app.services.ai.cad_branch_evidence import merge_vertical_candidates
        native={'devices':[{'tag':tag,'name':'RCBO','category':'RCBO','quantity':1,'spec':'2P 20A 6kA',
            'source_observations':{'extraction_method':'native'}} for tag in ('P19','P20')],
            'boxes':[{'device_id':str(i),'symbol_box_2d':[100,100+i*100,120,120+i*100],
                'load_box_2d':[700,100+i*100,800,120+i*100]} for i in range(2)]}
        parts=[{'devices':[{'name':'MCB','category':'MCB','tag':'P19','quantity':1,
                    'source_observations':{'circuit':{'power_w':100}}},
                    {'name':'MCB','category':'MCB','quantity':1,'spec':'Spare'}],
                'boxes':[{'device_id':'0','symbol_box_2d':[100,100,120,120]},
                         {'device_id':'1','symbol_box_2d':[100,400,120,420]}]}]
        merge_vertical_candidates(parts,[{'box_2d':[0,0,1000,1000]}],native)
        self.assertEqual([r.get('tag') for r in parts[0]['devices']],['P19',None,'P20'])
        self.assertEqual(parts[0]['devices'][0]['category'],'RCBO')
        self.assertEqual(parts[0]['devices'][0]['source_observations']['circuit']['power_w'],100)
        self.assertEqual(parts[0]['boxes'][1]['symbol_box_2d'],[100,400,120,420])

    def test_generic_as_does_not_assert_three_cts_without_a_source_multiplier(self):
        from app.services.ai.cad_symbol_seeds import ground_ct_clusters
        for text,expected in (('AS',1),('3xTI 80/5A',3)):
            parts=[{'devices':[{'name':'CT','category':'CT','quantity':3,'drawing_quantity':1,
                'unit':'Cái','quantity_basis':'Nguồn 3 pha nối AS'}]}]
            ground_ct_clusters({'labels':[{'text':'AS'},{'text':text}]},parts)
            row=parts[0]['devices'][0];self.assertEqual(row['quantity'],expected)
            if expected==1:
                self.assertEqual(row['unit'],'Cụm');self.assertTrue(row['quantity_review']['blocking'])

    def test_native_shared_heading_proposes_values_but_does_not_certify_proximity(self):
        from app.services.ai.cad_branch_evidence import propose_vertical_ratings
        labels=[{'id':str(i),'text':text,'x':100,'y':800-i*15,'height':10,
                 'bounds':[100,790-i*15,130,800-i*15]} for i,text in enumerate(('RCBO','2P','25A','6kA'))]
        labels.append({'id':'load','text':'P9. BẾP TỪ','x':300,'y':200,'height':10,'bounds':[295,100,305,300]})
        for ambiguous in (False,True):
            extra=[{'id':'ambiguous','text':'3P','x':100,'y':780,'height':10,'bounds':[100,770,130,780]}] if ambiguous else []
            evidence={'view_bounds':[0,0,1000,1000],'labels':labels+extra}
            parts=[{'devices':[{'name':'MCB nhánh','category':'MCB','tag':'P9','spec':'1P 25A',
                'quantity':1,'poles':1,'in_a':25}],
                'boxes':[{'device_id':'0','symbol_box_2d':[180,300,220,320]}]}]
            propose_vertical_ratings(evidence,parts)
            row=parts[0]['devices'][0]
            self.assertEqual(row['category'],'MCB' if ambiguous else 'RCBO')
            self.assertEqual(row['poles'],1 if ambiguous else 2)
            self.assertNotIn('verified',parts[0]['boxes'][0])
            if not ambiguous:
                self.assertNotIn('source_evidence_ids',row)
                self.assertTrue(parts[0]['boxes'][0]['shared_label'])
                self.assertIn('requires_pixel',row['source_observations']['native_heading_candidate']['method'])

    def test_dense_vertical_groups_split_at_label_gaps_and_keep_the_shared_source_parent(self):
        from app.services.ai.cad_branch_evidence import split_native_columns
        parent={'box_2d':[100,50,950,950],'rotation_degrees':0}
        labels=[{'text':f'P{i+1}. BẾP TỪ','bounds':[100+i*75,100,110+i*75,300]} for i in range(10)]
        source={'view_bounds':[0,0,1000,1000],'labels':labels}
        groups=split_native_columns([parent],source)
        self.assertEqual([g['native_branch_tags'] for g in groups],
            [[f'P{i}' for i in range(1,6)],[f'P{i}' for i in range(6,11)]])
        self.assertEqual(groups[0]['box_2d'][3],groups[1]['box_2d'][1])
        self.assertTrue(all(g['native_parent_box_2d']==parent['box_2d'] for g in groups))
        self.assertEqual(split_native_columns([parent],{**source,'labels':labels[:7]}),[parent])

    def test_explicit_fan_quantity_note_is_kept_once_without_fabricating_a_rating(self):
        from app.services.ai.material_note_evidence import native_material_notes
        source={'view_bounds':[0,0,100,100],'labels':[{'id':'fan-note',
            'text':'GẮN 2 QUẠT TẢN NHIỆT CHO TỦ','bounds':[10,80,60,84]}]}
        parts=[{'devices':[],'boxes':[],'notes':[]}]
        native_material_notes(source,parts);native_material_notes(source,parts)
        self.assertEqual(len(parts[0]['devices']),1)
        self.assertEqual(parts[0]['devices'][0]['quantity'],2)
        self.assertEqual(parts[0]['devices'][0]['spec'],'')
        self.assertEqual(parts[0]['boxes'][0]['evidence_kind'],'material_note')
        self.assertNotIn('note_verified',parts[0]['boxes'][0])

    def test_dol_rectangles_bind_to_their_own_load_instead_of_the_logo_contactor(self):
        from app.services.ai.cad_branch_evidence import seed_control_label_boxes
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.dxf';doc=ezdxf.new();msp=doc.modelspace()
            for x,label,load in ((20,'DOL','QUẠT HÚT'),(100,'DOL','QUẠT GIÓ TƯƠI'),(170,'Contactor','LOGO')):
                msp.add_lwpolyline([(x,100),(x+15,100),(x+15,110),(x,110)],close=True)
                msp.add_text(label,dxfattribs={'insert':(x+1,102),'height':3})
                msp.add_text(load,dxfattribs={'insert':(x+7,20),'height':2,'rotation':90})
            doc.saveas(path)
            devices=[{'name':'DOL','category':'DOL','spec':'DOL','connected_load':load}
                     for load in ('QUẠT HÚT','QUẠT GIÓ TƯƠI')]
            boxes=seed_control_label_boxes(path,[0,0,1,1],devices,[])
            self.assertEqual(len(boxes),2)
            self.assertLess(boxes[0]['symbol_box_2d'][1],boxes[1]['symbol_box_2d'][1])
            self.assertEqual([b['load_label'] for b in boxes],['QUẠT HÚT','QUẠT GIÓ TƯƠI'])
            self.assertTrue(all(b['geometry_source']=='native_cad_control_rectangle' for b in boxes))

    def test_native_schedule_keeps_repeated_spares_and_explicit_neutral_without_inventing_ratings(self):
        from app.services.ai.cad_branch_evidence import native_schedule_candidates
        labels=[];rows=[]
        specs=['MCB-1P-10A-6kA','RCBO-1P+N-25A-30mA-6kA','MCB-1P-32A-6kA','RCBO-1P+N-20A-30mA-6kA']
        for i,spec in enumerate(specs):
            y=800-i*100;tag='L1' if i==0 else 'S1' if i==1 else 'DP'
            labels.extend([{'id':f't{i}','text':tag,'x':500,'y':y,'height':10,'bounds':[500,y,520,y+10]},
                {'id':f'r{i}','text':spec,'x':200,'y':y,'height':10,'bounds':[200,y,350,y+10]}])
            rows.append({'id':f't{i}','rating_id':f'r{i}','tag':tag,'rating':spec})
        result=native_schedule_candidates({'view_bounds':[0,0,1000,1000],'labels':labels,'rows':rows})
        self.assertEqual(len(result['devices']),4)
        self.assertEqual([r['poles'] for r in result['devices']],[1,2,1,2])
        self.assertEqual([r['in_a'] for r in result['devices']],[10,25,32,20])
        self.assertNotEqual(result['devices'][2]['source_evidence_ids'],result['devices'][3]['source_evidence_ids'])
        self.assertTrue(all('audit_observed' not in r for r in result['boxes']))

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

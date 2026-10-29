import json
import unittest
from unittest.mock import AsyncMock
from PIL import Image,ImageDraw
from app.services.ai.branch_label_review import branch_bands
from app.services.ai.response_parser import ResponseParserService
from app.services.ai.source_semantic_review import review_panel_inventory,preserve_transcribed_label


class SourceSemanticReviewTests(unittest.IsolatedAsyncioTestCase):
    def row(self,**changes):
        return dict(category='MCCB',name='Nhánh',panel_code='P',spec='3P 125A',
            quantity=1,in_a=125,poles=3,**changes)

    async def test_uses_actual_ct_label_instead_of_previous_wrong_ratio(self):
        row=dict(category='CT',name='CT',panel_code='P',spec='630/5',quantity=3,
            drawing_quantity=1,procurement_quantity=3,quantity_basis='Bộ đo ba pha',
            source_observations={'spec_label':'Ti 500/5','category_label':'Ti'})
        _,devices=await review_panel_inventory(AsyncMock(return_value=json.dumps({'devices':[row]})),[],'P')
        self.assertEqual(devices[0].spec,'Ti 500/5')
        self.assertEqual(devices[0].quantity,3)
        self.assertEqual(devices[0].drawing_quantity,1)

    async def test_blank_spare_is_not_grouped_with_adjacent_rated_feeders(self):
        row=self.row();row.update(quantity=5,drawing_quantity=5,source_observations={
            'spec_label':'125A/3P','category_label':'MCCB','branch_observations':[
                {'tag':'WP'+str(i),'spec_label':'125A/3P' if i<7 else '',
                 'category_label':'MCCB' if i<7 else ''} for i in range(3,8)]})
        _,devices=await review_panel_inventory(AsyncMock(return_value=json.dumps({'devices':[row]})),[],'P')
        self.assertEqual([d.quantity for d in devices],[4,1])
        self.assertEqual(devices[0].in_a,125)
        self.assertEqual(devices[1].spec,'')
        self.assertIsNone(devices[1].in_a)
        self.assertIsNone(devices[1].poles)
        self.assertEqual(devices[1].tag,'WP7')

    async def test_missing_source_transcription_marks_review(self):
        _,devices=await review_panel_inventory(AsyncMock(return_value=json.dumps({'devices':[self.row()]})),[],'P')
        self.assertEqual(devices[0].quantity_review['status'],'needs_review')

    async def test_wrong_panel_cannot_replace_source(self):
        row=self.row();row['panel_code']='OTHER'
        with self.assertRaises(ValueError):
            await review_panel_inventory(AsyncMock(return_value=json.dumps({'devices':[row]})),[],'P')

    async def test_isolated_source_rows_clear_a_neighbor_rating(self):
        image=Image.new('RGB',(900,500),'white');draw=ImageDraw.Draw(image)
        for y in (100,180,260):draw.line((400,y,870,y),fill='black',width=2)
        self.assertEqual(len(branch_bands(image)),3)
        rows=[]
        for index in range(1,4):
            row=self.row();row.update(tag='WP'+str(index),source_observations={
                'spec_label':'125A/3P','category_label':'MCCB','branch_labels':['WP'+str(index)]})
            rows.append(row)
        strips={'rows':[dict(row_index=i,tag='WP'+str(i),spec_label='125A/3P' if i<3 else '',category_label='MCCB') for i in range(1,4)]}
        _,reviewed=await review_panel_inventory(AsyncMock(return_value=json.dumps({'devices':rows})),[],'P',
            image=image,call_image=AsyncMock(return_value=json.dumps(strips)))
        self.assertEqual(reviewed[1].in_a,125)
        self.assertEqual(reviewed[2].spec,'')
        self.assertIsNone(reviewed[2].in_a)
        self.assertEqual(reviewed[2].quantity_review['status'],'needs_review')

    async def test_separately_observed_component_is_retained_for_review(self):
        old=ResponseParserService.parse_device_list(json.dumps({'devices':[dict(category='FUSE',name='Fuse',spec='',panel_code='P',quantity=1)]}))
        _,reviewed=await review_panel_inventory(AsyncMock(return_value=json.dumps({'devices':[self.row()]})),old,'P',
            source_counts=[{'category':'FUSE','quantity':1}])
        self.assertEqual(reviewed[-1].category,'FUSE')
        self.assertEqual(reviewed[-1].quantity_review['status'],'needs_review')

    def test_later_wrong_crop_cannot_replace_transcribed_ratio_or_fill_blank_spare(self):
        devices=ResponseParserService.parse_device_list(json.dumps({'devices':[
            dict(category='CT',name='CT',spec='Ti 500/5',quantity=3,source_observations={'spec_label':'Ti 500/5'}),
            dict(category='MCCB',name='Spare',spec='',quantity=1,source_observations={'spec_label':''})]}))
        self.assertTrue(preserve_transcribed_label(devices[0],{'source_spec':'Ti 630/5'}))
        self.assertTrue(preserve_transcribed_label(devices[1],{'source_spec':'125A/3P','in_a':125}))
        self.assertEqual(devices[0].spec,'Ti 500/5')
        self.assertEqual(devices[1].spec,'')
        self.assertIsNone(devices[1].in_a)

    async def test_split_preserves_reasoned_material_multiplier(self):
        row=self.row();row.update(quantity=4,drawing_quantity=2,procurement_quantity=4,
            quantity_basis='Hai bộ lặp cùng cấu hình, mỗi bộ có hai lộ.',technical_analysis='Hai lộ trên mỗi bộ, hai bộ cần bốn CB.',
            source_observations={'spec_label':'125A/3P','category_label':'MCCB','branch_observations':[
                {'tag':'L1','spec_label':'125A/3P','category_label':'MCCB'},
                {'tag':'L2','spec_label':'','category_label':'MCCB'}]})
        _,devices=await review_panel_inventory(AsyncMock(return_value=json.dumps({'devices':[row]})),[],'P')
        self.assertEqual([d.quantity for d in devices],[2,2])
        self.assertEqual([d.drawing_quantity for d in devices],[1,1])

if __name__=='__main__':unittest.main()

import unittest
from copy import deepcopy
from app.services.catalog_complementary_views import merge_complementary_views


class ComplementaryViewTests(unittest.TestCase):
    def item(self,id,face,poles='2P'):
        return {'id':id,'display':'MCB CHINT NXB-63','product_code':'NXB-63','brand':'CHINT',
                'type':'MCB','spec':{'so_cuc':poles,'nhan_block_nguon':id},'views':[
                    {'id':id+'-view','face':face,'preview':'/equipment-library/'+id+'/preview'}],
                'primary_view':id+'-view'}

    def test_join_complementary_views_keep_asset_owner_and_separate_poles(self):
        rows=merge_complementary_views([self.item('side','Mặt bên'),self.item('front','Mặt trước'),self.item('other','Mặt trước','3P')])
        self.assertEqual(len(rows),2)
        merged=next(p for p in rows if p['spec']['so_cuc']=='2P')
        self.assertEqual(merged['id'],'front')
        self.assertEqual(len(merged['views']),2)
        self.assertEqual(merged['primary_view'],'front-view')
        self.assertIn('2P',merged['display'])
        self.assertEqual(merged['views'][0]['preview'],'/equipment-library/side/preview')
        again=merge_complementary_views(deepcopy(rows))
        self.assertEqual(again,rows)

    def test_do_not_join_same_face_unknown_configuration_or_conflicting_specs(self):
        a=self.item('a','Mặt trước');b=self.item('b','Mặt trước')
        self.assertEqual(len(merge_complementary_views(deepcopy([a,b]))),2)
        b['views'][0]['face']='Mặt bên';b['spec']['dong_dinh_muc_A']=32
        self.assertEqual(len(merge_complementary_views(deepcopy([a,b]))),2)
        a['spec']={};b['spec']={}
        self.assertEqual(len(merge_complementary_views([a,b])),2)


if __name__=='__main__':unittest.main()

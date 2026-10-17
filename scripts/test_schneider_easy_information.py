import unittest
from scripts.import_schneider_easy_information import pairs

class SchneiderTableTests(unittest.TestCase):
    def test_same_row_required(self):
        desc=('125 A EasyPact EZC250F 3P3d 18kA',(150,100,300,110))
        right=('EZC250F3125',(418,100,490,110))
        self.assertEqual(pairs([desc,right])[0][2]['Số cực'],'3P')
        self.assertEqual(pairs([desc,('EZC250F3125',(418,115,490,125))]),[])
        self.assertEqual(pairs([desc,right,('EZC250F3160',(500,100,570,110))]),[])
    def test_other_frame_and_poles_are_not_inferred(self):
        desc=('63 A EasyPact EZCV250H 4P 36kA with earth leakage',(150,100,390,110))
        self.assertEqual(pairs([desc,('EZC250H4063',(418,100,490,110))]),[])
        row=pairs([desc,('EZCV250H4063',(418,100,490,110))])[0]
        self.assertEqual(row[2]['Số cực'],'4P')
        self.assertEqual(row[2]['Bảo vệ dòng rò'],'Có')

if __name__=='__main__':unittest.main()

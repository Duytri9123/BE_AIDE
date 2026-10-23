import unittest

from app.services.cad.catalogtb_assets import face_code


class ExplicitProjectionTests(unittest.TestCase):
    def test_lateral_labels_with_state_keep_their_projection(self):
        for label in ('Mặt bên trái', 'Mặt bên phải · Nắp đóng'):
            self.assertEqual(face_code(label), 'side')

    def test_reference_views_are_not_front_or_cutout(self):
        self.assertEqual(face_code('Hình trục đo'), 'isometric')
        self.assertEqual(face_code('Mặt đế gá theo bản vẽ'), 'mounting')
        self.assertEqual(face_code('Lỗ khoét cánh'), 'cutout')

    def test_uncertain_labels_remain_unresolved(self):
        for label in (None, 'Chưa xác định hướng nhìn', 'CAD thiếu đường nét', 'CAD còn nhiều mặt'):
            self.assertEqual(face_code(label), 'unknown')


if __name__ == '__main__':
    unittest.main()

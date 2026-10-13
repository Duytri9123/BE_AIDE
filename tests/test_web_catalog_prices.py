import importlib.util
from pathlib import Path
import unittest
from bs4 import BeautifulSoup

spec=importlib.util.spec_from_file_location('refresh_web_catalog',Path(__file__).resolve().parents[1]/'scripts/refresh_web_catalog.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class SellerPriceTests(unittest.TestCase):
    def test_sale_price_is_not_original_price(self):
        html='<span class="price"><del><span class="woocommerce-Price-amount">714.960 ₫</span></del><ins><span class="woocommerce-Price-amount">390.000 ₫</span></ins></span>'
        self.assertEqual(module.selling_price(BeautifulSoup(html,'html.parser').span),390000)
    def test_price_range_and_foreign_currency_are_not_single_vnd_offers(self):
        for html in ('<span><span class="woocommerce-Price-amount">300.000 ₫</span>–<span class="woocommerce-Price-amount">500.000 ₫</span></span>', '<span><span class="woocommerce-Price-amount">50 USD</span></span>'):
            self.assertIsNone(module.selling_price(BeautifulSoup(html,'html.parser').span))

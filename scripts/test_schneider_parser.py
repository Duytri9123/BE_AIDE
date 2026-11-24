"""
Test suite for pricebook matching across manufacturers (Schneider, LS Electric, Mitsubishi, etc.)
Verifies that Vietnamese designations and technical aliases correctly resolve to corresponding catalog codes.
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add backend directory to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root_dir))
load_dotenv(root_dir / '.env')

from app.services.ai.takeoff_pricebook import match_device, link_devices, published_rows
from app.services.ai.quotation_selection import select_quotation_devices
from app.services.ai.compatible_brand_selection import compatible_brand_replacements
from app.services.device_catalog_browser import build_catalog_page, load_supplier_items


def test_rcbo_matching_ls_electric():
    """Verify that generic CAD tag RCBO-1P+N 16A 6kA 30mA correctly matches LS Electric LB63N 1P+N."""
    rows = published_rows()
    dev = {
        'category': 'RCBO',
        'brand': 'LS Electric',
        'part_number': 'RCBO-1P+N',
        'name': 'Aptomat chống dòng rò và quá dòng (RCBO)',
        'spec': '1P+N · 16A-6kA-30mA',
        'poles': 1.0,
        'in_a': 16.0,
        'icu_ka': 6.0,
        'pole_configuration': '1P+N',
    }

    match = match_device(dev, rows)
    assert match['candidate_count'] > 0, "LS RCBO must return candidates"
    best = match['candidates'][0]
    assert best['brand'] == 'LS Electric', f"Expected LS Electric, got {best['brand']}"
    assert best['sku'] == 'LB63N 1P+N', f"Expected LB63N 1P+N, got {best['sku']}"
    assert best['price'] == 626000, f"Expected 626,000 VND, got {best['price']}"

    linked = link_devices([dev], rows)[0]
    assert linked['part_number'] == 'LB63N 1P+N', f"Expected part_number updated to LB63N 1P+N, got {linked['part_number']}"
    print("PASS: test_rcbo_matching_ls_electric")


def test_brand_switch_schneider_to_ls():
    """Verify switching brand from Schneider Electric to LS Electric maps RCBO to LB63N 1P+N."""
    schneider_dev = {
        'category': 'RCBO',
        'brand': 'Schneider Electric',
        'part_number': 'A9D31616',
        'name': 'Aptomat chống dòng rò và quá dòng (RCBO)',
        'spec': '1P+N · 16A-6kA-30mA',
        'poles': 1.0,
        'in_a': 16.0,
        'icu_ka': 6.0,
        'pole_configuration': '1P+N',
    }

    replaced, changed = compatible_brand_replacements([schneider_dev], 'LS Electric')
    assert changed == 1, f"Expected 1 device changed, got {changed}"
    assert replaced[0]['brand'] == 'LS Electric'
    assert replaced[0]['part_number'] == 'LB63N 1P+N'
    assert replaced[0]['unit_price'] == 626000
    print("PASS: test_brand_switch_schneider_to_ls")


def test_catalog_vietnamese_search():
    """Verify that Vietnamese search queries correctly find English and Vietnamese catalog entries."""
    items = load_supplier_items()
    queries = {
        'rcbo': 8,
        'chống rò': 8,
        'aptomat chống rò': 8,
        'chống giật': 8,
        'relay nhiệt': 9,
    }
    for q, min_expected in queries.items():
        res = build_catalog_page([], [], supplier_items=items, brand='LS Electric', q=q)
        assert res['total'] >= min_expected, f"Query '{q}' returned {res['total']} items, expected at least {min_expected}"
    print("PASS: test_catalog_vietnamese_search")


if __name__ == '__main__':
    test_rcbo_matching_ls_electric()
    test_brand_switch_schneider_to_ls()
    test_catalog_vietnamese_search()
    print("\nALL PRICEBOOK & CLASSIFICATION TESTS PASSED!")

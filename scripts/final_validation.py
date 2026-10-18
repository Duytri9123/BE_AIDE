#!/usr/bin/env python3
"""
Final validation script - Kiểm tra tất cả file catalog đã cập nhật
"""
import json
from pathlib import Path
from typing import Dict, List, Tuple

CATALOG_ROOT = Path(__file__).parent.parent / "data" / "CatalogTB"

def validate_json_file(filepath: Path) -> Tuple[bool, str]:
    """Validate JSON syntax của một file"""
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
        return True, "OK"
    except json.JSONDecodeError as e:
        return False, f"JSON Error: {e}"
    except Exception as e:
        return False, f"Error: {e}"

def check_gia_ban_structure(filepath: Path) -> Tuple[bool, str, Dict]:
    """Kiểm tra cấu trúc trường gia_ban"""
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)

        if 'gia_ban' not in data:
            return False, "Missing gia_ban", {}

        gia_ban = data['gia_ban']
        required_fields = ['don_gia', 'don_vi_tien_te', 'trang_thai', 'hang',
                          'nguon_tham_khao', 'ngay_cap_nhat', 'muc_do_tin_cay']

        missing = [f for f in required_fields if f not in gia_ban]
        if missing:
            return False, f"Missing fields: {missing}", gia_ban

        return True, "Complete", gia_ban

    except Exception as e:
        return False, f"Error: {e}", {}

def scan_all_files() -> Dict:
    """Quét tất cả các file và validate"""
    results = {
        'total': 0,
        'valid_json': 0,
        'invalid_json': 0,
        'has_gia_ban': 0,
        'missing_gia_ban': 0,
        'complete_structure': 0,
        'incomplete_structure': 0,
        'has_real_price': 0,
        'no_price': 0,
        'errors': []
    }

    for brand_dir in CATALOG_ROOT.iterdir():
        if not brand_dir.is_dir() or brand_dir.name.startswith('_'):
            continue

        thiet_bi_dir = brand_dir / "ThietBi"
        if not thiet_bi_dir.exists():
            continue

        for device_dir in thiet_bi_dir.iterdir():
            if not device_dir.is_dir():
                continue

            info_file = device_dir / "thong_tin_thiet_bi.json"
            if not info_file.exists():
                continue

            results['total'] += 1

            # Validate JSON
            is_valid, msg = validate_json_file(info_file)
            if is_valid:
                results['valid_json'] += 1
            else:
                results['invalid_json'] += 1
                results['errors'].append({
                    'file': str(info_file.relative_to(CATALOG_ROOT.parent.parent)),
                    'error': msg
                })
                continue

            # Check gia_ban structure
            has_structure, status, gia_ban = check_gia_ban_structure(info_file)

            if 'gia_ban' in status or has_structure:
                results['has_gia_ban'] += 1

                if has_structure:
                    results['complete_structure'] += 1

                    # Check if has real price
                    if gia_ban.get('don_gia') and gia_ban['don_gia'] != '-':
                        results['has_real_price'] += 1
                    else:
                        results['no_price'] += 1
                else:
                    results['incomplete_structure'] += 1
                    results['errors'].append({
                        'file': str(info_file.relative_to(CATALOG_ROOT.parent.parent)),
                        'error': status
                    })
            else:
                results['missing_gia_ban'] += 1
                results['errors'].append({
                    'file': str(info_file.relative_to(CATALOG_ROOT.parent.parent)),
                    'error': 'Missing gia_ban field'
                })

    return results

def print_report(results: Dict):
    """In báo cáo kết quả"""
    print("\n" + "="*80)
    print("📊 FINAL VALIDATION REPORT - BÁO CÁO XÁC THỰC CUỐI CÙNG")
    print("="*80)

    print(f"\n✅ JSON SYNTAX VALIDATION:")
    print(f"   Total files scanned: {results['total']}")
    print(f"   Valid JSON: {results['valid_json']} ({results['valid_json']/results['total']*100:.1f}%)")
    print(f"   Invalid JSON: {results['invalid_json']}")

    print(f"\n✅ GIA_BAN FIELD CHECK:")
    print(f"   Has gia_ban field: {results['has_gia_ban']} ({results['has_gia_ban']/results['total']*100:.1f}%)")
    print(f"   Missing gia_ban: {results['missing_gia_ban']}")
    print(f"   Complete structure: {results['complete_structure']} ({results['complete_structure']/results['total']*100:.1f}%)")
    print(f"   Incomplete structure: {results['incomplete_structure']}")

    print(f"\n💰 PRICE DATA:")
    print(f"   Has real price: {results['has_real_price']} ({results['has_real_price']/results['total']*100:.1f}%)")
    print(f"   No price (marked '-'): {results['no_price']} ({results['no_price']/results['total']*100:.1f}%)")

    if results['errors']:
        print(f"\n❌ ERRORS FOUND ({len(results['errors'])}):")
        for i, err in enumerate(results['errors'][:10], 1):  # Show first 10
            print(f"   {i}. {err['file']}")
            print(f"      Error: {err['error']}")
        if len(results['errors']) > 10:
            print(f"   ... and {len(results['errors']) - 10} more errors")
    else:
        print(f"\n✨ NO ERRORS FOUND! All files are valid.")

    print("\n" + "="*80)

    # Final verdict
    if results['invalid_json'] == 0 and results['missing_gia_ban'] == 0:
        print("🎉 VERDICT: ✅ PASS - All files validated successfully!")
    elif results['invalid_json'] > 0:
        print("⚠️ VERDICT: ❌ FAIL - Some files have JSON syntax errors")
    elif results['missing_gia_ban'] > 0:
        print("⚠️ VERDICT: ⚠️ WARNING - Some files missing gia_ban field")

    print("="*80 + "\n")

if __name__ == "__main__":
    print("🔍 Starting final validation...")
    results = scan_all_files()
    print_report(results)

    # Save report
    report_file = Path(__file__).parent.parent / "docs" / "VALIDATION_REPORT.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"VALIDATION REPORT - {results}\n")

    print(f"💾 Report saved to: {report_file}")

"""Publish documented NDK choices without assigning a model to unlabelled CAD."""
import json
from scripts.complete_catalog_references import ROOT, CAT, ndk_references


def main():
    relative = 'Chint/ThietBi/Control_Transformer/thong_tin_thiet_bi.json'
    path = CAT / relative
    raw = json.loads(path.read_text(encoding='utf8'))
    reference = raw['catalog_tham_khao']
    reference['options'] = ndk_references()
    reference['updated_at'] = '2026-10-17'
    raw['muc_do_xac_nhan'] = 'Nguồn ghi MBA - Chint; 16 mã NDK đã tra catalog hãng để lựa chọn. Chưa xác định mã của CAD nguồn.'
    raw['tu_khoa_tim_kiem'] = list(dict.fromkeys([
        *(x for x in raw['tu_khoa_tim_kiem'] if x and x != 'Mặt trước'),
        *(o['model'] for o in reference['options'])]))
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    overlay_path = ROOT/'app/data/catalogtb_published_information.json'
    overlay = json.loads(overlay_path.read_text(encoding='utf8'))
    overlay['profiles'][relative]['catalog_tham_khao'] = reference
    overlay_path.write_text(json.dumps(overlay, ensure_ascii=False, separators=(',',':'))+'\n', encoding='utf8')
    from app.services.catalogtb_browser import _build_browser_data, _snapshot_path
    from scripts.refresh_catalogtb_offline_information import refresh_from_snapshot
    snapshot = _build_browser_data()
    _snapshot_path().write_text(json.dumps(snapshot, ensure_ascii=False), encoding='utf8')
    refresh_from_snapshot(snapshot)
    print('Published 16 documented NDK model choices; source CAD model remains unassigned.')


if __name__ == '__main__':
    main()

"""Report actual family evidence separately from generic populated tables."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAT = ROOT/'data/CatalogTB'
STRONG = {'catalog_family_match', 'catalog_function_match'}


def main():
    path = ROOT/'docs/catalog-reference-completion.json'
    report = json.loads(path.read_text(encoding='utf8'))
    active = []
    for row in report['items']:
        raw = json.loads((CAT/row['profile']).read_text(encoding='utf-8-sig'))
        choices = raw['catalog_tham_khao']['options']
        row['family_rows'] = sum(o['basis'] in STRONG for o in choices)
        row['related_series_rows'] = sum(o['basis']=='catalog_series_reference' for o in choices)
        if not raw.get('browser_hidden'):
            active.append(row)
    report.update(family_matched_profiles=sum(bool(r['family_rows']) for r in report['items']),
                  family_information_rows=sum(r['family_rows'] for r in report['items']),
                  related_series_profiles=sum(bool(r['related_series_rows']) for r in report['items']),
                  related_series_information_rows=sum(r['related_series_rows'] for r in report['items']))
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    summary = {k:v for k,v in report.items() if k!='items'}
    summary.update(active_profiles=len(active),
                   active_family_matched_profiles=sum(bool(r['family_rows']) for r in active),
                   active_related_series_profiles=sum(bool(r['related_series_rows']) for r in active),
                   active_without_commercial_reference=sum(r['missing_model'] for r in active))
    audit = dict(summary=summary, scope='All source profiles and all existing supplier/web catalog rows; no price imported',
                 items=report['items'])
    (ROOT/'docs/catalog-family-link-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    note=(f"Ghép theo hãng/dòng hoặc chức năng: {report['family_matched_profiles']} hồ sơ, "
          f"{report['family_information_rows']} dòng thông tin. Dòng liên quan cùng hãng/loại: "
          f"{report['related_series_profiles']} hồ sơ, {report['related_series_information_rows']} dòng; "
          'ghi riêng vì mã/khung có thể khác. Không lấy giá. Có bảng tham khảo không chứng minh đã nhận diện đúng dòng thiết bị.')
    md=ROOT/'docs/catalog-reference-completion.md'
    lines=md.read_text(encoding='utf8').splitlines()
    lines=[note if line.startswith('Ghép theo hãng/dòng') else line for line in lines]
    md.write_text('\n'.join(lines)+'\n',encoding='utf8')
    (ROOT/'docs/catalog-family-link-audit.md').write_text('\n'.join([
        '# Rà soát ghép thông tin bảng giá với CAD — 16/10/2026','',
        f"Đã rà toàn bộ {report['profiles']} hồ sơ nguồn ({len(active)} đang dùng; giao diện gộp thành 1304 mục), đối chiếu 9581 dòng bảng giá/website hiện có.",'',
        note,'',
        '- Giữ mọi biến thể trong dòng đã ghép, kể cả cùng mã ở nhiều nguồn. Hãng, mã, thông số, tài liệu được giữ; giá để `---`.',
        '- Đọc số cực từ nhận diện CAD; không lấy các mã đã bổ sung vào từ khóa tìm kiếm làm bằng chứng nhận diện.',
        '- BKN-LS 1P/2P/3P: mỗi cấu hình có hai biến thể BKN sẵn có tương ứng; không lấy LA125H thay cho BKN.',
        '- TIMER 24H CHINT: KG316T AC220V, 24h/7, NO, mã hàng 309010, bảng CHINT trang 73; không lấy JSS48A thay cho timer lịch.',
        '- MC12AF: các biến thể MC-12a; S8FS-C05024J lấy đúng mã nguồn; mở rộng cùng cơ chế cho toàn bộ hồ sơ.',
        '- Chặn ghép nhầm loại, ghép số thuần, và tiền tố LC1D9 với LC1D95; đọc các mã thành viên để hỗ trợ dải dòng.',
        f"- {summary['active_without_commercial_reference']} hồ sơ đang dùng chưa có mã thương mại tham khảo cụ thể. Số này khác số hồ sơ chưa ghép đúng dòng: không dùng việc bảng có dữ liệu để kết luận tất cả đã đúng.",
        '', 'Chi tiết từng hồ sơ: `catalog-family-link-audit.json`.',''
    ]),encoding='utf8')
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':
    main()

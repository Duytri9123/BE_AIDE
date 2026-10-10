"""Public product research, separate from takeoff and CAD acceptance."""
import re
from urllib.parse import urlparse
from app.services.cad.catalogtb_assets import category_matches

MANUFACTURER_DOMAINS = {
    'ls': ('lselectric.com', 'lselectric.co.kr'),
    'chint': ('chintglobal.com', 'chint.com', 'chint.net'),
    'schneider': ('se.com',), 'schneider electric': ('se.com',),
    'abb': ('abb.com',), 'omron': ('omron.com', 'omron.eu'),
}


def brand_key(value):
    return re.sub(r'[^a-z0-9]', '', str(value or '').lower().replace('electric', ''))


def compact_summary(answer):
    lines = [re.sub(r'^\s*[-*•]\s*', '', line).replace('**', '').strip()
             for line in str(answer or '').splitlines() if re.match(r'^\s*[-*•]\s+', line)]
    if not lines:
        lines = re.split(r'(?<=[.!?])\s+', str(answer or '').strip())
    # Keep whole facts, including units. Never truncate a current/voltage mid-sentence.
    selected = [line for line in lines if 0 < len(line) <= 180][:3]
    return '\n'.join(selected)


def product_information(device, engine, search=None):
    brand = str(device.get('brand') or '').strip()
    unknown = brand_key(brand) in ('', 'asian', 'unknown', 'chuarõ', 'khongro')
    model = str(device.get('part_number') or '').strip()
    model_key = re.sub(r'[^a-z0-9]', '', model.lower())
    matches, related = [], []
    for profile in engine.reference_profiles:
        if not category_matches(str(device.get('category') or '').upper(), profile['category']):
            continue
        if device.get('poles') and profile.get('poles'):
            p = re.fullmatch(r'\s*(\d+)\s*P?\s*', str(profile['poles']), re.I)
            if not p or int(p[1]) != int(device['poles']): continue
        names = [profile.get('series'), profile.get('sku'), *(profile.get('search_aliases') or [])]
        exact = bool(model_key) and any(re.sub(r'[^a-z0-9]', '', str(n or '').lower()) == model_key for n in names)
        actual = str(profile.get('brand') or '').strip()
        same = not unknown and bool(actual) and brand_key(brand) == brand_key(actual)
        row = {'name': profile['name'], 'brand': actual or 'Asian',
               'model': profile.get('series'), 'model_match': exact,
               'brand_match': 'same' if same else 'unknown' if unknown or not actual else 'different',
               'status': 'model_reference' if exact else 'related_reference',
               'reference_path': profile['reference_path'], 'fabrication_ready': False}
        (matches if exact else related).append(row)
    related.sort(key=lambda r: (r['brand_match'] != 'same', r['name']))
    sources = []
    for r in (search or {}).get('results', []):
        url = str(r.get('url') or '')
        parsed = urlparse(url)
        if parsed.scheme not in ('https', 'http') or not parsed.hostname: continue
        expected = MANUFACTURER_DOMAINS.get(brand.lower(), ())
        source_name = str(r.get('title') or '').strip().lower()
        direct_primary = any(parsed.hostname == d or parsed.hostname.endswith('.'+d) for d in expected)
        # Grounding redirects carry the source's host as their title. Retain the
        # attribution but never treat a generated answer segment as a datasheet excerpt.
        grounded_primary = parsed.hostname == 'vertexaisearch.cloud.google.com' and any(source_name == d or source_name.endswith('.'+d) for d in expected)
        if expected and not (direct_primary or grounded_primary): continue
        sources.append({'title': str(r.get('title') or parsed.hostname)[:200], 'url': url,
                        'snippet': '' if grounded_primary else str(r.get('snippet') or '')[:250],
                        'source_type': 'manufacturer' if direct_primary or grounded_primary else 'unverified_reference'})
    return {'brand': brand or 'Asian', 'model': model or None,
            'ai_summary': compact_summary((search or {}).get('answer')) if sources else '',
            'web_status': 'sources_found' if sources else 'no_sources' if search and search.get('success') else 'unavailable',
            'sources': sources[:3], 'system_matches': matches[:6], 'related_products': related[:3],
            'match_status': 'model_reference_found' if matches else 'model_not_verified' if model else 'model_unspecified',
            'note': 'Match model trong thư viện không xác nhận thông số điện, mặt CAD hoặc khả năng chế tạo.'}

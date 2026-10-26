"""Manufacturer-backed assembly guidance; never generates a procurement BOM."""
import json
from functools import lru_cache
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / 'data' / 'assembly_symbol_knowledge.json'


@lru_cache(maxsize=1)
def load_assembly_knowledge():
    data = json.loads(PATH.read_text(encoding='utf-8'))
    if data.get('schema_version') != '1.0' or not data.get('profiles'):
        raise ValueError('Invalid assembly knowledge schema')
    identities = set()
    for profile in data['profiles']:
        if profile['id'] in identities or not profile.get('functional_core'):
            raise ValueError('Duplicate or incomplete assembly profile')
        identities.add(profile['id'])
        if not profile.get('source_ids') or any(key not in data['sources'] for key in profile['source_ids']):
            raise ValueError('Assembly profile lacks source provenance')
    return data


def assembly_prompt_context():
    data = load_assembly_knowledge()
    # References guide interpretation only. The output contract still belongs
    # to the caller, and source-specific evidence determines quantities/SKUs.
    context = {key: data[key] for key in ('reviewed_on', 'policy', 'profiles')}
    return ('\nTHƯ VIỆN KÝ HIỆU BỘ THIẾT BỊ ĐÃ ĐỐI CHIẾU TÀI LIỆU HÃNG: '
            'Chỉ áp dụng mục khớp ngữ cảnh nguồn. Các thành phần chức năng không phải BOM mua rời; '
            'không suy mọi tùy chọn đều có trong bộ. Giữ hợp đồng JSON của yêu cầu.\n'
            + json.dumps(context, ensure_ascii=False, separators=(',', ':')) + '\n')

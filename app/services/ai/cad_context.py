"""Bound individual CAD requests without silently dropping source labels."""


def transcript_chunks(transcript, max_chars=24000):
    """Prefer whole spatial columns; retain even unusually long source labels."""
    import re
    sections = re.split(r'(?=\n--- \[Nhánh / Cột tọa độ X)', transcript)
    chunks, current = [], ''
    for section in sections:
        # Split an oversized column only at line boundaries, never inside a label.
        units = section.splitlines(keepends=True) if len(section) > max_chars else [section]
        for unit in units:
            if current and len(current) + len(unit) > max_chars:
                chunks.append(current)
                current = ''
            current += unit
    if current:
        chunks.append(current)
    return chunks or ['']


def merge_chunk_devices(existing, additions):
    """Deduplicate explicit panel/tag identities, never identical untagged symbols."""
    def normalized(value):
        return ' '.join(str(value or '').casefold().split())

    result = list(existing)
    keyed = {(normalized(d.panel_code), normalized(d.tag)): d for d in result if d.tag}
    warnings = []
    for device in additions:
        key = (normalized(device.panel_code), normalized(device.tag))
        if device.tag and key in keyed:
            old = keyed[key]
            if any(normalized(getattr(old, field, None)) != normalized(getattr(device, field, None))
                   for field in ('category', 'spec', 'quantity')):
                warnings.append('Các lượt đọc CAD chưa thống nhất thông số/số lượng của '
                                + str(device.panel_code or '') + '/' + str(device.tag) + '; cần đối chiếu nguồn.')
            continue
        result.append(device)
        if device.tag:
            keyed[key] = device
    return result, warnings

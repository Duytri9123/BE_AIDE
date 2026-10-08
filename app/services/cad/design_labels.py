"""Display selected design ratings; frame-size CAD names are never electrical ratings."""
import re


def effective_spec(device):
    proposal = device.get('compatible_proposal') or {}
    applied = proposal.get('applied') is True or proposal.get('status') in ('accepted', 'applied', 'approved')
    if applied and proposal.get('compatibility_verified') is True and proposal.get('proposed_spec'):
        return str(proposal['proposed_spec'])
    return str(device.get('spec') or '')


def rating_text(device):
    spec = effective_spec(device)
    match = re.search(r'(?<![\d.])(\d+(?:\.\d+)?)\s*A\b', spec, re.I)
    value = match.group(1) if match else device.get('in_a')
    return f'{float(value):g}A' if value is not None else ''

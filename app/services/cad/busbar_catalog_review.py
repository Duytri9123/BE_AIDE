"""Busbar proposals use only CatalogTB and require verified electrical ratings."""
from app.services.cad.catalogtb_assets import assets, category_matches

def review(current,required_length_mm=None):
    # Discovery must include fabrication templates and unconfirmed projections.
    # Their presence does not make them a front view or an electrically rated bar.
    references = [a for a in assets() if category_matches('BUSBAR', a['category'])]
    return dict(status='catalogtb_rating_verification_required', selected=None,
        catalogtb_reference_count=len(references), required_length_mm=required_length_mm,
        catalogtb_references=[dict(asset_id=a['id'], name=a['name'], face=a['face'],
            profile=a['profile_path'], placement_allowed=a['placement'].get('cho_phep_chen') is not False)
            for a in references],
        stock_length_is_route_length=False, neutral_section_policy='do_not_reduce_without_load_and_harmonic_review',
        release_ready=False, required=['verified_rating','temperature_rise','ambient','short_circuit','supports','terminal_joint','clearance','neutral_harmonics'])

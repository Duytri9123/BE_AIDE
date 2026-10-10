"""Busbar proposals use only CatalogTB and require verified electrical ratings."""
from app.services.cad.catalogtb_assets import candidates

def review(current,required_length_mm=None):
    references = candidates('BUSBAR')
    return dict(status='catalogtb_rating_verification_required', selected=None,
        catalogtb_reference_count=len(references), required_length_mm=required_length_mm,
        stock_length_is_route_length=False, neutral_section_policy='do_not_reduce_without_load_and_harmonic_review',
        release_ready=False, required=['verified_rating','temperature_rise','ambient','short_circuit','supports','terminal_joint','clearance','neutral_harmonics'])

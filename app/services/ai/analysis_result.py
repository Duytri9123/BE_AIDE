from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.schemas.ai import AnalysisResultSchema, ExtractedDeviceSchema
from app.services.cad.enclosure_cad_generator import EnclosureCadGeneratorService

def _build_analysis_result_schema(
    session_id: Any,
    iteration_number: int,
    raw_devices: List[Any],
    conf_scores: Optional[dict] = None,
    iteration_id: Optional[int] = None,
    cad_file_info: Optional[dict] = None,
    quotation_file_info: Optional[dict] = None,
    enclosure_spec: Optional[dict] = None,
) -> AnalysisResultSchema:
    conf = conf_scores or {}
    if conf.get('source_configuration') == 'quotation' and conf.get('design_devices'):
        raw_devices = conf['design_devices']
    if 'panel_designs' in conf:
        cad_file_info = next((r.get('cad_file') for r in (conf.get('panel_designs') or {}).values() if r.get('cad_file')), None)
    elif 'design_result' in conf and 'cad_file' in conf['design_result']:
        cad_file_info = conf['design_result']['cad_file']
    panel_images: Dict[str, str] = {}
    cleaned_devices = []

    from app.services.ai.auxiliary_devices import expand_devices
    for d in expand_devices(raw_devices):
        payload = dict(d) if isinstance(d, dict) else (d.model_dump() if hasattr(d, "model_dump") else dict(d))
        payload.setdefault("category", "Thiết bị")
        payload.setdefault("name", "Thiết bị")
        payload.setdefault("spec", "")
        payload.setdefault("quantity", 1)
        payload.setdefault("confidence", 0.95)

        # Deduplicate massive base64 panel_evidence_image to keep payload light
        p_img = payload.get("panel_evidence_image")
        if p_img and len(p_img) > 100:
            filename = payload.get("source_filename")
            page = payload.get("source_page")
            key = (f"{filename}::page::{page}" if filename and page is not None
                   else filename or payload.get("panel_code") or "default")
            if key not in panel_images:
                panel_images[key] = p_img
            if "default" not in panel_images:
                panel_images["default"] = p_img
            payload["panel_evidence_image"] = None

        cleaned_devices.append(ExtractedDeviceSchema.model_validate(payload))

    # Capture any existing panel_images map
    if isinstance(conf.get("panel_images"), dict):
        for k, v in conf["panel_images"].items():
            if k not in panel_images:
                panel_images[k] = v

    enc_spec = enclosure_spec or conf.get("enclosure_spec")
    if not enc_spec:
        enc_devs = [
            {k: v for k, v in d.model_dump().items() if k not in ("evidence_image", "panel_evidence_image")}
            for d in cleaned_devices
        ]
        try:
            enc_spec = EnclosureCadGeneratorService.calculate_enclosure_specs(enc_devs)
        except ValueError as exc:
            enc_spec = {"status": "needs_dimensions", "review_note": str(exc)}
    elif isinstance(enc_spec, dict) and "branch_rows" in enc_spec:
        clean_rows = []
        for row in enc_spec["branch_rows"]:
            if isinstance(row, list):
                clean_rows.append([
                    {k: v for k, v in b.items() if k not in ("evidence_image", "panel_evidence_image")}
                    if isinstance(b, dict) else b
                    for b in row
                ])
            else:
                clean_rows.append(row)
        enc_spec = {**enc_spec, "branch_rows": clean_rows}

    return AnalysisResultSchema(
        source_configuration=conf.get('source_configuration') or 'schematic',
        session_id=session_id,
        iteration_id=iteration_id,
        iteration_number=iteration_number,
        devices=cleaned_devices,
        warnings=conf.get("warnings", []),
        topology_preview={
            "incomer_a": enc_spec.get("incomer_rating", settings.DEFAULT_INCOMER_RATING) if enc_spec else settings.DEFAULT_INCOMER_RATING,
            "feeders_count": len(cleaned_devices)
        },
        enclosure_spec=enc_spec,
        panel_images=panel_images,
        evidence_overviews=conf.get("evidence_overviews") or {},
        cad_file=cad_file_info,
        cad_status=(conf.get('design_result') or {}).get('cad_status'),
        cad_blockers=(conf.get('design_result') or {}).get('cad_blockers') or [],
        cad_layout=conf.get('cad_layout'),
        panel_designs=[{'panel_code': code, **result} for code, result in (conf.get('panel_designs') or {}).items()],
        quotation_file=quotation_file_info,
        quotation_rows=conf.get("quotation_rows") or [],
        technical_proposals=conf.get("technical_proposals") or [],
        conclusion=conf.get("conclusion"),
        panel_info=conf.get("panel_info"),
        panels=conf.get("panels") or [],
        technical_audit=conf.get("technical_audit"),
        file_assessment=conf.get("file_assessment") or {},
        files_assessment=conf.get("files_assessment") or [],
        circuit_assessment=conf.get("circuit_assessment") or {},
        overall_assessment=conf.get("overall_assessment") or {},
        execution_logs=conf.get("execution_logs") or [],
        process_steps=conf.get("process_steps") or [],
        physical_layout=conf.get("physical_layout"),
        layout_conflicts=conf.get("layout_conflicts") or [],
        analysis_mode=conf.get("analysis_mode", "sld_takeoff"),
        log_version=conf.get("log_version", 2),
    )

from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.schemas.ai import AnalysisResultSchema, ExtractedDeviceSchema

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
    from app.services.export.quotation_names import quotation_display_rows
    conf = conf_scores or {}
    # The extraction table remains the source observation. Approved quotation
    # changes are stored as design_devices, not substituted into source evidence.
    if 'panel_designs' in conf:
        cad_file_info = next((r.get('cad_file') for r in (conf.get('panel_designs') or {}).values() if r.get('cad_file')), None)
    elif 'design_result' in conf and 'cad_file' in conf['design_result']:
        cad_file_info = conf['design_result']['cad_file']
    panel_images: Dict[str, str] = {}
    cleaned_devices = []

    from app.services.ai.auxiliary_devices import expand_devices
    from app.services.ai.metering_selection import enrich_metering_selection
    from app.services.ai.takeoff_catalog import refresh_meter_catalog
    from app.services.ai.procurement_review import SECTION_ORDER, quotation_section
    for d in refresh_meter_catalog(enrich_metering_selection(expand_devices(raw_devices))):
        payload = dict(d) if isinstance(d, dict) else (d.model_dump() if hasattr(d, "model_dump") else dict(d))
        payload.setdefault("category", "Thiết bị")
        payload.setdefault("name", "Thiết bị")
        payload['spec'] = str(payload.get('spec') or '').strip()

        # Tự động suy luận thông số kỹ thuật (spec) chuẩn khi bản vẽ/dữ liệu lưu chưa có:
        if not payload['spec'] or payload['spec'].lower() in {'chưa xác định', 'không ghi', 'không rõ'}:
            cat_u = str(payload.get('category') or '').upper().strip()
            name_l = str(payload.get('name') or '').lower().strip()
            tag_l = str(payload.get('tag') or '').lower().strip()

            if cat_u in {'LIGHT', 'PILOT_LIGHT'} or 'đèn báo' in name_l or 'báo pha' in name_l:
                payload['spec'] = '2A'
                payload['in_a'] = 2.0
            elif cat_u in {'SHUNT_TRIP', 'SHT', 'TRIP'} or 'cuộn cắt' in name_l or 'shunt' in name_l or tag_l in {'s/t', 'sht', 'mx'}:
                payload['spec'] = '200-240VAC'
            elif cat_u in {'ELR', 'EFR'} or 'rò đất' in name_l or 'chạm đất' in name_l:
                payload['spec'] = '0.03-30A 220VAC'
            elif cat_u == 'ZCT' or 'zct' in name_l or 'thứ tự không' in name_l:
                payload['spec'] = 'Ø80mm'
            elif cat_u == 'CT' or 'biến dòng' in name_l:
                in_rating = int(payload.get('in_a')) if payload.get('in_a') else 150
                payload['spec'] = f'{in_rating}/5A'
            elif cat_u in {'SELECTOR_SWITCH', 'SELECTOR', 'VSS', 'VOLT_SELECTOR'} or 'chuyển mạch' in name_l:
                payload['spec'] = '4 vị trí 0-5A' if ('ampe' in name_l or 'ass' in tag_l) else '7 vị trí 0-500V'
            elif cat_u in {'VOLTMETER', 'METER'} or 'đồng hồ' in name_l or 'vôn kế' in name_l:
                payload['spec'] = '0-150A' if 'ampe' in name_l else '0-500V'
            elif cat_u == 'TIMER' or 'timer' in name_l or 'hẹn giờ' in name_l:
                payload['spec'] = '24h 220VAC 16A'
            elif cat_u in {'FUSE', 'FUSE_HOLDER'} or 'cầu chì' in name_l:
                payload['spec'] = '2A 500V'

        payload.setdefault("quantity", 1)
        payload.setdefault("confidence", 0.95)
        section = quotation_section(payload)
        if section in SECTION_ORDER:
            payload['section'] = section

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

        from app.services.ai.device_facts import enrich_device_facts
        cleaned_devices.append(ExtractedDeviceSchema.model_validate(enrich_device_facts(payload)))

    from app.services.ai.panel_identity import normalize_panel_identities
    # Panel devices are rebuilt below. Avoid copying their stored image payloads.
    from copy import deepcopy
    conf = dict(conf)
    source_panels = deepcopy([{k: v for k, v in panel.items() if k != 'devices'}
                              for panel in (conf.get('panels') or [])])
    normalize_panel_identities(cleaned_devices, source_panels)
    merged_panels = {}
    for panel in source_panels:
        code = panel.get('panel_code')
        if code and code not in merged_panels:
            merged_panels[code] = {**panel, 'devices': []}
    for device in cleaned_devices:
        code = device.panel_code
        if code:
            # Device images are already present in the top-level device list.
            # A second copy in each panel makes saved revisions very expensive
            # to download, parse, cache and render.
            merged_panels.setdefault(code, {'panel_code':code,'panel_name':device.panel_name,'devices':[]})['devices'].append(
                device.model_dump(exclude={'evidence_image','evidence_images','panel_evidence_image'}))
    conf['panels'] = list(merged_panels.values())

    # Capture any existing panel_images map
    if isinstance(conf.get("panel_images"), dict):
        for k, v in conf["panel_images"].items():
            if k not in panel_images:
                panel_images[k] = v

    enc_spec = enclosure_spec or conf.get("enclosure_spec")
    if not enc_spec:
        # Opening a saved takeoff is a read, not a CAD sizing run. Cabinet
        # dimensions and construction details are produced by the design step.
        enc_spec = {'status': 'pending_design',
                    'review_note': 'Thông số vỏ tủ và bố trí được bổ sung khi tạo thiết kế.'}
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
        quotation_rows=quotation_display_rows(conf.get("quotation_rows") or [],
            devices=conf.get('design_devices') or [d.model_dump() for d in cleaned_devices]),
        user_prompt=conf.get('user_prompt'),
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

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict
from uuid import UUID

from app.core.config import settings
from app.core.validators import DeviceValidator, ProjectValidator


class AnalyzeStartRequest(BaseModel):
    project_id: int
    file_id: Optional[int] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    fallback_to_standard_template: Optional[bool] = False
    user_prompt: Optional[str] = None
    target_page: Optional[int] = None
    is_new_session: Optional[bool] = False
    
    @field_validator('project_id')
    @classmethod
    def validate_project_id(cls, v):
        return ProjectValidator.validate_project_id(v)


class AnalyzePromptRequest(BaseModel):
    project_id: int
    prompt: str
    fallback_to_standard_template: Optional[bool] = False
    
    @field_validator('project_id')
    @classmethod
    def validate_project_id(cls, v):
        return ProjectValidator.validate_project_id(v)


class AnalyzeRefineRequest(BaseModel):
    session_id: UUID
    user_corrections: List[dict]
    user_message: Optional[str] = None
    focus_zone: Optional[str] = None


class AnalyzeFinalizeRequest(BaseModel):
    session_id: UUID


class TechnicalProposalSchema(BaseModel):
    original_device: str = ""
    original_spec: str = ""
    ai_analysis: str = ""
    proposed_device: str = ""
    proposed_spec: str = ""
    suggested_brand: Optional[str] = ""
    technical_reason: Optional[str] = ""


class ExtractedDeviceSchema(BaseModel):
    cad: Optional[dict] = None
    category: str
    name: str
    spec: str
    in_a: Optional[float] = None
    icu_ka: Optional[float] = None
    poles: Optional[int] = None
    quantity: int = 1
    drawing_quantity: Optional[int] = None
    procurement_quantity: Optional[int] = None
    quantity_basis: Optional[str] = None
    quantity_confidence: Optional[float] = None
    brand: Optional[str] = None
    detected_brand: Optional[str] = None
    selection_source: Optional[str] = None
    part_number: Optional[str] = None
    section: Optional[str] = None
    location: Optional[str] = None
    panel_code: Optional[str] = None
    panel_name: Optional[str] = None
    notes: Optional[str] = None
    tag: Optional[str] = None
    mounting: Optional[str] = None
    electrical_function: Optional[str] = None
    upstream_device: Optional[str] = None
    downstream_device: Optional[str] = None
    connected_load: Optional[str] = None
    physical_location: Optional[dict] = None
    confidence: float = 0.0
    box_2d: Optional[List[int]] = None
    evidence_image: Optional[str] = None
    panel_evidence_image: Optional[str] = None
    evidence_region: Optional[dict] = None
    source_type: Optional[str] = None
    source_filename: Optional[str] = None
    source_page: Optional[int] = None
    suggested_brands: Optional[List[str]] = None
    technical_match_note: Optional[str] = None
    catalog_matches: Optional[dict] = None
    is_alternative_recommended: Optional[bool] = False
    original_spec: Optional[str] = None
    compatibility_note: Optional[str] = None
    suggested_alternatives: Optional[List[dict]] = None
    accompanying_accessories: Optional[List[dict]] = None
    inferred_components: Optional[List[dict]] = None
    compatible_proposal: Optional[dict] = None
    
    @field_validator('in_a')
    @classmethod
    def validate_current(cls, v):
        return DeviceValidator.validate_current_rating(v)
    
    @field_validator('icu_ka')
    @classmethod
    def validate_icu(cls, v):
        return DeviceValidator.validate_icu_rating(v)
    
    @field_validator('poles')
    @classmethod
    def validate_poles(cls, v):
        return DeviceValidator.validate_poles(v)
    
    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v):
        return DeviceValidator.validate_quantity(v)
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        return DeviceValidator.validate_confidence(v)

    @field_validator('box_2d')
    @classmethod
    def normalize_evidence_box(cls, v):
        """Accept only a non-empty [ymin, xmin, ymax, xmax] box on 0..1000."""
        if not isinstance(v, (list, tuple)) or len(v) != 4:
            return None
        try:
            ymin, xmin, ymax, xmax = [
                max(0, min(1000, int(round(float(value))))) for value in v
            ]
        except (TypeError, ValueError):
            return None
        if ymax <= ymin or xmax <= xmin:
            return None
        return [ymin, xmin, ymax, xmax]
    
    @field_validator('category')
    @classmethod
    def normalize_category(cls, v):
        return v.upper() if v else "OTHER"


class AnalysisResultSchema(BaseModel):
    session_id: UUID
    iteration_id: Optional[int] = None
    iteration_number: int
    devices: List[ExtractedDeviceSchema]
    warnings: List[str]
    topology_preview: dict
    enclosure_spec: Optional[dict] = None
    panel_images: Dict[str, str] = Field(default_factory=dict)
    cad_file: Optional[dict] = None
    quotation_file: Optional[dict] = None
    quotation_rows: List[dict] = Field(default_factory=list)
    technical_proposals: List[dict] = Field(default_factory=list)
    conclusion: Optional[dict] = None
    panel_info: Optional[dict] = None
    panels: List[dict] = Field(default_factory=list)
    technical_audit: Optional[dict] = None
    file_assessment: dict = Field(default_factory=dict)
    files_assessment: List[dict] = Field(default_factory=list)
    circuit_assessment: dict = Field(default_factory=dict)
    overall_assessment: dict = Field(default_factory=dict)
    execution_logs: List[dict] = Field(default_factory=list)
    process_steps: List[dict] = Field(default_factory=list)
    physical_layout: Optional[dict] = None
    layout_conflicts: List[dict] = Field(default_factory=list)
    analysis_mode: str = "sld_takeoff"
    log_version: int = 2

    @field_validator(
        "quotation_rows",
        "technical_proposals",
        "panels",
        "files_assessment",
        "execution_logs",
        "process_steps",
        "layout_conflicts",
        mode="before",
    )
    @classmethod
    def normalize_result_lists(cls, value):
        return value if isinstance(value, list) else []

    @field_validator("file_assessment", "overall_assessment", mode="before")
    @classmethod
    def normalize_result_objects(cls, value):
        return value if isinstance(value, dict) else {}

    @model_validator(mode="after")
    def ensure_panel_envelope(self):
        """Keep historical/text results in the same panel envelope as file inputs."""
        if self.devices and (not self.technical_audit or "cluster_review" not in self.technical_audit):
            from app.services.ai.system_completeness import technical_audit
            self.technical_audit = technical_audit(self.devices)
        if self.panels or not self.devices:
            return self
        grouped = {}
        for device in self.devices:
            code = str(device.panel_code or "CHUA_XAC_DINH").strip()
            name = str(device.panel_name or "Tủ điện chưa xác định").strip()
            device.panel_code = code
            device.panel_name = name
            panel = grouped.setdefault(code, {
                "panel_code": code,
                "panel_name": name,
                "location": str(device.location or "").strip(),
                "enclosure_dimensions": "",
                "dimension": "",
                "page": device.source_page,
                "devices": [],
            })
            panel["devices"].append(device.model_dump())
        self.panels = list(grouped.values())
        return self


class CadMacroBlockSchema(BaseModel):
    id: str
    type: str  # e.g., 'ENCLOSURE_BODY', 'BUSBAR_SYSTEM', 'INCOMER_UNIT', 'FEEDER_ROW', 'ACCESSORY_PANEL', 'TITLEBLOCK', 'DIMENSIONS'
    name: str
    layer: str
    command_line: str
    bounds: Optional[dict] = None  # {x, y, w, h}
    metadata: Optional[dict] = None


class ChatRequest(BaseModel):
    session_id: Optional[UUID] = None
    project_id: int
    message: str
    current_devices: Optional[List[dict]] = None
    context: Optional[dict] = None
    
    @field_validator('project_id')
    @classmethod
    def validate_project_id(cls, v):
        return ProjectValidator.validate_project_id(v)
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError("Message không được rỗng")
        if len(v) > 10000:
            raise ValueError("Message quá dài (max 10000 characters)")
        return v.strip()


class ChatResponse(BaseModel):
    reply: str
    action_type: str = "general_chat"  # 'macro_draft', 'update_devices', 'resize_panel', 'general_chat'
    macro_blocks: Optional[List[CadMacroBlockSchema]] = None
    enclosure_specs: Optional[dict] = None
    devices: Optional[List[ExtractedDeviceSchema]] = None
    quotation_rows: Optional[List[dict]] = None
    cad_file: Optional[dict] = None
    cad_commands: Optional[List[str]] = None
    suggested_corrections: Optional[List[dict]] = None
    artifacts: Optional[List[dict]] = None

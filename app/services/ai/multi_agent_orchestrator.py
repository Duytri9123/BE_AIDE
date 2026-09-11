"""
Multi-Agent Orchestrator cho BOM Extraction
Sử dụng nhiều agent chuyên biệt chạy iteratively để cải thiện kết quả
"""
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from app.core.logging_config import get_logger, LogContext
from app.core.exceptions import AIVisionError
from app.core.config import settings
from app.core.constants import (
    COMPLEXITY_SIMPLE_MAX_DEVICES,
    COMPLEXITY_STANDARD_MAX_DEVICES,
    COMPLEXITY_COMPLEX_MAX_DEVICES,
    CABINET_HEIGHT_BASE_MM,
    CABINET_HEIGHT_PER_DEVICE_MM,
    CABINET_HEIGHT_MIN_MM,
    CABINET_HEIGHT_MAX_MM,
    CABINET_DEPTH_HEAVY_MM,
    CABINET_DEPTH_LIGHT_MM,
    CABINET_WIDTH_INCOMER_LARGE_A,
    CABINET_WIDTH_INCOMER_MEDIUM_A,
    MAX_FILENAME_LENGTH,
)
from app.services.ai.vision_analyzer import VisionAnalyzerService
from app.services.ai.multi_panel_detector import MultiPanelDetector, Panel

logger = get_logger(__name__)


class AgentRole(str, Enum):
    """Vai trò của các agent trong hệ thống"""
    VISION_EXTRACTOR = "vision_extractor"      # Trích xuất thiết bị từ hình ảnh
    SPEC_VALIDATOR = "spec_validator"          # Validate và chuẩn hóa specs
    CATALOG_MATCHER = "catalog_matcher"        # Khớp với catalog có sẵn
    QUOTATION_BUILDER = "quotation_builder"    # Xây dựng báo giá chuẩn
    CAD_GENERATOR = "cad_generator"            # Sinh file CAD theo template
    QUALITY_CHECKER = "quality_checker"        # Kiểm tra chất lượng kết quả


@dataclass
class AgentMessage:
    """Message trao đổi giữa các agents"""
    from_agent: AgentRole
    to_agent: AgentRole
    iteration: int
    content: Dict
    confidence: float = 0.0
    feedback: Optional[str] = None


@dataclass
class ExtractionState:
    """Trạng thái của quá trình extraction qua các vòng lặp"""
    iteration: int = 0
    devices: List[Dict] = field(default_factory=list)
    panels: List[Panel] = field(default_factory=list)  # Detected panels
    quotation_rows: List[Dict] = field(default_factory=list)
    quotation_rows_by_panel: Dict[str, List[Dict]] = field(default_factory=dict)  # Per-panel quotations
    cad_commands: List[str] = field(default_factory=list)
    enclosure_spec: Dict = field(default_factory=dict)
    confidence_score: float = 0.0
    feedback_history: List[str] = field(default_factory=list)
    completed_agents: List[AgentRole] = field(default_factory=list)


class MultiAgentOrchestrator:
    """
    Orchestrator điều phối nhiều agents chạy iteratively
    
    Flow:
    1. VisionExtractor: Trích xuất thô từ hình ảnh (iteration 0)
    2. SpecValidator: Validate và chuẩn hóa (iteration 1)
    3. CatalogMatcher: Khớp với DB có sẵn (iteration 2)
    4. QualityChecker: Đánh giá và feedback (iteration 3)
    5. Nếu confidence < threshold: Quay lại VisionExtractor với feedback
    6. QuotationBuilder: Xây dựng báo giá theo template (iteration final-1)
    7. CADGenerator: Sinh file CAD theo mẫu (iteration final)
    """
    
    def __init__(
        self,
        max_iterations: Optional[int] = None,
        confidence_threshold: Optional[float] = None,
        provider: Optional[str] = None,
        api_key: str = "",
        model: str = ""
    ):
        self.max_iterations = max_iterations if max_iterations is not None else settings.ORCHESTRATOR_MAX_ITERATIONS
        self.confidence_threshold = confidence_threshold if confidence_threshold is not None else settings.ORCHESTRATOR_CONFIDENCE_THRESHOLD
        self.provider = provider or ""
        self.api_key = api_key
        self.model = model
        if not self.provider or not self.model:
            raise ValueError("Provider và model phải được chọn cụ thể trong cấu hình BE.")
        
        # Template prompts cho từng agent
        self._load_agent_prompts()
    
    def _load_agent_prompts(self):
        """Load prompts cho từng agent role"""
        self.prompts = {
            AgentRole.VISION_EXTRACTOR: self._get_vision_extractor_prompt(),
            AgentRole.SPEC_VALIDATOR: self._get_spec_validator_prompt(),
            AgentRole.CATALOG_MATCHER: self._get_catalog_matcher_prompt(),
            AgentRole.QUOTATION_BUILDER: self._get_quotation_builder_prompt(),
            AgentRole.CAD_GENERATOR: self._get_cad_generator_prompt(),
            AgentRole.QUALITY_CHECKER: self._get_quality_checker_prompt(),
        }
    
    async def orchestrate(
        self,
        image_path: str,
        project_name: str,
        catalog_data: Optional[Dict] = None,
        cad_templates: Optional[List[Dict]] = None,
        quotation_template: Optional[Dict] = None
    ) -> ExtractionState:
        """
        Main orchestration flow - chạy các agents theo sequence
        
        Args:
            image_path: Đường dẫn đến sơ đồ điện (single line diagram)
            project_name: Tên dự án (ví dụ: "TỦ ĐIỆN TSXD-630A")
            catalog_data: Database catalog thiết bị có sẵn
            cad_templates: Mẫu CAD có sẵn trong DB
            quotation_template: Template báo giá chuẩn
        
        Returns:
            ExtractionState với kết quả cuối cùng sau các iterations
        """
        state = ExtractionState()
        
        with LogContext(project_name=project_name, image_path=image_path):
            logger.info(f"Starting multi-agent orchestration, max_iterations={self.max_iterations}")
            
            for iteration in range(self.max_iterations):
                state.iteration = iteration
                logger.info(f"=== Iteration {iteration} ===")
                
                # Step 1: Vision Extraction (hoặc re-extraction với feedback)
                if iteration == 0 or state.confidence_score < self.confidence_threshold:
                    state = await self._run_vision_extractor(
                        state, image_path, project_name
                    )
                
                # Step 2: Spec Validation
                if AgentRole.VISION_EXTRACTOR in state.completed_agents:
                    state = await self._run_spec_validator(state)
                
                # Step 3: Catalog Matching
                if AgentRole.SPEC_VALIDATOR in state.completed_agents and catalog_data:
                    state = await self._run_catalog_matcher(state, catalog_data)
                
                # Step 4: Quality Check
                if AgentRole.CATALOG_MATCHER in state.completed_agents:
                    state = await self._run_quality_checker(state)
                    
                    # Nếu đạt confidence threshold → proceed to final steps
                    if state.confidence_score >= self.confidence_threshold:
                        logger.info(
                            f"Confidence threshold reached: {state.confidence_score:.2f}",
                            extra={"iteration": iteration}
                        )
                        break
                    else:
                        # Feedback loop - sẽ re-run vision extractor ở iteration tiếp theo
                        logger.warning(
                            f"Confidence below threshold: {state.confidence_score:.2f} < {self.confidence_threshold}",
                            extra={"iteration": iteration}
                        )
            
            # Final Steps: Build outputs
            # Step 4.5: Detect multiple panels
            state.panels = MultiPanelDetector.detect_panels(
                state.devices,
                project_name
            )
            
            logger.info(
                f"Detected {len(state.panels)} panel(s)",
                extra={
                    "panel_count": len(state.panels),
                    "panels": [p.name for p in state.panels]
                }
            )
            
            # Step 5: Quotation Building
            if quotation_template:
                if len(state.panels) == 1:
                    # Single panel → 1 quotation
                    state = await self._run_quotation_builder(
                        state, project_name, quotation_template
                    )
                else:
                    # Multiple panels → 1 quotation per panel + 1 consolidated
                    state = await self._run_multi_panel_quotation_builder(
                        state, project_name, quotation_template
                    )
            
            # Step 6: CAD Generation
            if cad_templates:
                state = await self._run_cad_generator(
                    state, project_name, cad_templates
                )
            
            logger.info(
                f"Multi-agent orchestration completed",
                extra={
                    "total_iterations": state.iteration + 1,
                    "final_confidence": state.confidence_score,
                    "device_count": len(state.devices),
                    "quotation_rows": len(state.quotation_rows)
                }
            )
            
            return state
    
    async def _run_vision_extractor(
        self,
        state: ExtractionState,
        image_path: str,
        project_name: str
    ) -> ExtractionState:
        """
        Agent 1: Vision Extractor
        Trích xuất thiết bị từ sơ đồ điện single-line diagram
        """
        logger.info(f"Running VisionExtractor agent (iteration {state.iteration})")
        
        # Build prompt với feedback từ vòng trước (nếu có)
        prompt = self.prompts[AgentRole.VISION_EXTRACTOR].format(
            project_name=project_name,
            feedback="\n".join(state.feedback_history) if state.feedback_history else "Không có feedback"
        )
        
        try:
            # Call AI Vision API
            response = await VisionAnalyzerService.analyze_image(
                image_path=image_path,
                prompt=prompt,
                provider=self.provider,
                api_key=self.api_key,
                model=self.model
            )
            
            # Parse response
            from app.services.ai.response_parser import ResponseParserService
            devices = ResponseParserService.parse_device_list(response)
            
            # Update state
            state.devices = [
                {
                    "category": d.category,
                    "name": d.name,
                    "spec": d.spec,
                    "in_a": d.in_a,
                    "icu_ka": d.icu_ka,
                    "poles": d.poles,
                    "quantity": d.quantity,
                    "brand": d.brand,
                    "part_number": d.part_number,
                    "section": d.section,
                    "notes": d.notes,
                    "confidence": d.confidence,
                    "is_block": getattr(d, 'is_block', False),
                    "block_parent": getattr(d, 'block_parent', None)
                }
                for d in devices
            ]
            
            state.completed_agents.append(AgentRole.VISION_EXTRACTOR)
            
            logger.info(
                f"VisionExtractor extracted {len(state.devices)} devices",
                extra={"device_count": len(state.devices)}
            )
            
        except AIVisionError as e:
            logger.error(f"VisionExtractor failed: {str(e)}", exc_info=True)
            state.feedback_history.append(f"Vision extraction error: {str(e)}")
        
        return state
    
    async def _run_spec_validator(self, state: ExtractionState) -> ExtractionState:
        """
        Agent 2: Spec Validator
        Validate và chuẩn hóa specifications của thiết bị
        """
        logger.info(f"Running SpecValidator agent (iteration {state.iteration})")
        
        from app.core.validators import DeviceValidator
        
        # Validate từng device
        validated_devices = []
        validation_errors = []
        
        for idx, device in enumerate(state.devices):
            try:
                validated = DeviceValidator.validate_device_spec(
                    category=device.get("category", "OTHER"),
                    in_a=device.get("in_a"),
                    icu_ka=device.get("icu_ka"),
                    poles=device.get("poles"),
                    quantity=device.get("quantity", 1),
                    confidence=device.get("confidence", 0.85)
                )
                # Merge validated with original
                validated.update(device)
                validated_devices.append(validated)
            except Exception as e:
                validation_errors.append(f"Device {idx}: {str(e)}")
                logger.warning(f"Device {idx} validation failed: {str(e)}")
        
        # Update state
        state.devices = validated_devices
        
        if validation_errors:
            state.feedback_history.append(
                f"Spec validation issues: {'; '.join(validation_errors[:3])}"
            )
        
        state.completed_agents.append(AgentRole.SPEC_VALIDATOR)
        
        logger.info(
            f"SpecValidator validated {len(validated_devices)}/{len(state.devices)} devices",
            extra={
                "validated": len(validated_devices),
                "errors": len(validation_errors)
            }
        )
        
        return state
    
    async def _run_catalog_matcher(
        self,
        state: ExtractionState,
        catalog_data: Dict
    ) -> ExtractionState:
        """
        Agent 3: Catalog Matcher
        Khớp thiết bị với catalog có sẵn trong DB để lấy part_number, giá, etc.
        """
        logger.info(f"Running CatalogMatcher agent (iteration {state.iteration})")
        
        from app.services.device_catalog_engine import DeviceCatalogEngine
        
        catalog_engine = DeviceCatalogEngine.get_instance()
        matched_count = 0
        
        for device in state.devices:
            if not device.get("part_number") or device.get("part_number") == "":
                # Try to match from catalog
                matches = catalog_engine.filter_devices(
                    brand="ls_standard",
                    device_type=device.get("category"),
                    poles=device.get("poles"),
                    in_current=device.get("in_a"),
                    limit=1
                )
                
                if matches:
                    match = matches[0]
                    device["part_number"] = match.get("ma") or match.get("sku") or ""
                    device["catalog_matched"] = True
                    device["catalog_price"] = match.get("price")
                    matched_count += 1
                else:
                    # Fallback: generate part number
                    p_str = f"{device.get('poles')}P" if device.get('poles') else ""
                    a_str = f"{int(device.get('in_a'))}A" if device.get('in_a') else ""
                    device["part_number"] = f"LS-{device.get('category')}-{p_str}{a_str}".strip("-")
                    device["catalog_matched"] = False
        
        state.completed_agents.append(AgentRole.CATALOG_MATCHER)
        
        logger.info(
            f"CatalogMatcher matched {matched_count}/{len(state.devices)} devices",
            extra={"matched": matched_count, "total": len(state.devices)}
        )
        
        return state
    
    async def _run_quality_checker(self, state: ExtractionState) -> ExtractionState:
        """
        Agent 4: Quality Checker
        Đánh giá chất lượng extraction và tạo feedback để cải thiện
        
        ADAPTIVE: Tự động điều chỉnh expectations dựa trên project complexity
        """
        logger.info(f"Running QualityChecker agent (iteration {state.iteration})")
        
        # Detect project complexity
        complexity = self._detect_complexity(state)
        
        # Scoring criteria
        scores = {
            "device_count": 0.0,      # Có đủ thiết bị không?
            "completeness": 0.0,      # Specs đầy đủ không?
            "catalog_match": 0.0,     # Khớp với catalog không?
            "section_coverage": 0.0,  # Phủ đầy đủ các section không?
        }
        
        # 1. Device count - ADAPTIVE based on complexity
        expected_min = complexity["expected_min_devices"]
        expected_optimal = complexity["expected_optimal_devices"]
        
        if len(state.devices) >= expected_optimal:
            scores["device_count"] = 1.0
        elif len(state.devices) >= expected_min:
            # Linear scale from min to optimal
            scores["device_count"] = 0.7 + 0.3 * (
                (len(state.devices) - expected_min) / (expected_optimal - expected_min)
            )
        else:
            # Below minimum - proportional penalty
            scores["device_count"] = max(0.3, len(state.devices) / expected_min)
        
        # 2. Completeness (check if devices have key specs)
        complete_devices = 0
        for device in state.devices:
            if all([
                device.get("in_a") is not None,
                device.get("poles") is not None,
                device.get("part_number"),
            ]):
                complete_devices += 1
        scores["completeness"] = complete_devices / len(state.devices) if state.devices else 0
        
        # 3. Catalog match rate
        matched = sum(1 for d in state.devices if d.get("catalog_matched"))
        scores["catalog_match"] = matched / len(state.devices) if state.devices else 0
        
        # 4. Section coverage - ADAPTIVE based on complexity
        expected_sections = complexity["expected_sections"]
        found_sections = set(d.get("section") for d in state.devices if d.get("section"))
        
        if expected_sections:
            matched_sections = found_sections & expected_sections
            scores["section_coverage"] = len(matched_sections) / len(expected_sections)
        else:
            # For very simple projects, section coverage is less important
            scores["section_coverage"] = 0.8 if found_sections else 0.5
        
        # Weighted average - ADAPTIVE based on complexity
        weights = complexity["scoring_weights"]
        
        overall_confidence = sum(scores[k] * weights[k] for k in scores)
        state.confidence_score = overall_confidence
        
        # Generate feedback for next iteration - ADAPTIVE
        feedback_items = []
        
        # Device count feedback
        if scores["device_count"] < 0.6:
            if complexity["type"] == "simple":
                feedback_items.append(
                    f"Sơ đồ đơn giản: Cần ít nhất {expected_min} thiết bị. "
                    f"Hiện tại: {len(state.devices)}. Kiểm tra xem có thiết bị bị bỏ sót không?"
                )
            elif complexity["type"] == "complex":
                feedback_items.append(
                    f"Sơ đồ phức tạp: Cần ít nhất {expected_min} thiết bị. "
                    f"Hiện tại: {len(state.devices)}. Tập trung vào các khối/modules chưa được trích xuất."
                )
            else:
                feedback_items.append(
                    f"Cần trích xuất thêm thiết bị. Mục tiêu: {expected_optimal}, hiện tại: {len(state.devices)}"
                )
        
        # Completeness feedback
        if scores["completeness"] < 0.7:
            incomplete = sum(1 for d in state.devices if not all([
                d.get("in_a"),
                d.get("poles"),
                d.get("part_number")
            ]))
            feedback_items.append(
                f"{incomplete}/{len(state.devices)} thiết bị thiếu thông số kỹ thuật. "
                f"Focus vào trích xuất: Dòng định mức (A), Số cực (P), Model/Part Number"
            )
        
        # Catalog match feedback
        if scores["catalog_match"] < 0.6:
            feedback_items.append(
                f"Tỷ lệ khớp catalog thấp. Kiểm tra lại brand name và model number. "
                f"Ưu tiên: LS, Schneider, ABB, Siemens"
            )
        
        # Section coverage feedback
        if scores["section_coverage"] < 0.6 and complexity["type"] != "simple":
            missing = expected_sections - found_sections
            if missing:
                feedback_items.append(
                    f"Thiếu coverage sections: {', '.join(missing)}. "
                    f"Tìm kiếm các thiết bị thuộc sections này trên sơ đồ."
                )
        
        if feedback_items:
            state.feedback_history.append(
                f"Iteration {state.iteration} feedback: " + "; ".join(feedback_items)
            )
        
        state.completed_agents.append(AgentRole.QUALITY_CHECKER)
        
        logger.info(
            f"QualityChecker scored {overall_confidence:.2f}",
            extra={
                "confidence": overall_confidence,
                "scores": scores,
                "feedback_count": len(feedback_items)
            }
        )
        
        return state
    
    def _detect_complexity(self, state: ExtractionState) -> Dict:
        """
        Phát hiện độ phức tạp của project để điều chỉnh expectations
        
        Returns:
            {
                "type": "simple|standard|complex|very_complex",
                "expected_min_devices": int,
                "expected_optimal_devices": int,
                "expected_sections": set,
                "scoring_weights": dict,
                "has_blocks": bool
            }
        """
        device_count = len(state.devices)
        
        # Detect if project has blocks/modules
        has_blocks = any(
            "block" in d.get("name", "").lower() or
            "module" in d.get("name", "").lower() or
            "khối" in d.get("name", "").lower()
            for d in state.devices
        )
        
        # Classify complexity
        if device_count <= COMPLEXITY_SIMPLE_MAX_DEVICES:
            # SIMPLE: Sơ đồ rất đơn giản (1-3 thiết bị)
            complexity_type = "simple"
            expected_min = 1
            expected_optimal = 3
            expected_sections = {"Đầu vào"}  # Chỉ cần Incomer
            weights = {
                "device_count": 0.15,      # Ít quan trọng
                "completeness": 0.50,      # Rất quan trọng
                "catalog_match": 0.30,     # Quan trọng
                "section_coverage": 0.05   # Ít quan trọng
            }
        
        elif device_count <= COMPLEXITY_STANDARD_MAX_DEVICES:
            # STANDARD: Sơ đồ tiêu chuẩn (4-10 thiết bị)
            complexity_type = "standard"
            expected_min = 4
            expected_optimal = 10
            expected_sections = {"Đầu vào", "Đầu ra"}
            weights = {
                "device_count": 0.20,
                "completeness": 0.40,
                "catalog_match": 0.25,
                "section_coverage": 0.15
            }
        
        elif device_count <= COMPLEXITY_COMPLEX_MAX_DEVICES:
            # COMPLEX: Sơ đồ phức tạp (11-30 thiết bị)
            complexity_type = "complex"
            expected_min = 8
            expected_optimal = 25
            expected_sections = {"Đầu vào", "Đầu ra", "Đo lường & Giám sát"}
            weights = {
                "device_count": 0.25,
                "completeness": 0.35,
                "catalog_match": 0.20,
                "section_coverage": 0.20
            }
        
        else:
            # VERY_COMPLEX: Sơ đồ rất phức tạp (30+ thiết bị)
            complexity_type = "very_complex"
            expected_min = 15
            expected_optimal = 50
            expected_sections = {
                "Đầu vào",
                "Đầu ra",
                "Đo lường & Giám sát",
                "Điều khiển & Chiếu sáng"
            }
            weights = {
                "device_count": 0.30,
                "completeness": 0.30,
                "catalog_match": 0.15,
                "section_coverage": 0.25
            }
        
        # If has blocks, increase device count importance
        if has_blocks:
            weights["device_count"] += 0.10
            weights["section_coverage"] += 0.05
            # Normalize
            total = sum(weights.values())
            weights = {k: v/total for k, v in weights.items()}
        
        result = {
            "type": complexity_type,
            "expected_min_devices": expected_min,
            "expected_optimal_devices": expected_optimal,
            "expected_sections": expected_sections,
            "scoring_weights": weights,
            "has_blocks": has_blocks
        }
        
        logger.info(
            f"Detected complexity: {complexity_type}",
            extra={
                "complexity": complexity_type,
                "device_count": device_count,
                "expected_min": expected_min,
                "expected_optimal": expected_optimal,
                "has_blocks": has_blocks
            }
        )
        
        return result
    
    async def _run_quotation_builder(
        self,
        state: ExtractionState,
        project_name: str,
        template: Dict
    ) -> ExtractionState:
        """
        Agent 5: Quotation Builder
        Xây dựng báo giá theo template chuẩn (bảng vàng)
        """
        logger.info(f"Running QuotationBuilder agent")
        
        from app.services.export.quotation_builder import QuotationBuilderService
        
        # Build quotation rows theo template
        rows = QuotationBuilderService.build_rows_from_template(
            project_name=project_name,
            devices=state.devices,
            enclosure_spec=state.enclosure_spec,
            template=template
        )
        
        state.quotation_rows = rows
        state.completed_agents.append(AgentRole.QUOTATION_BUILDER)
        
        logger.info(
            f"QuotationBuilder generated {len(rows)} rows",
            extra={"row_count": len(rows)}
        )
        
        return state
    
    async def _run_multi_panel_quotation_builder(
        self,
        state: ExtractionState,
        project_name: str,
        template: Dict
    ) -> ExtractionState:
        """
        Agent 5B: Multi-Panel Quotation Builder
        Build separate quotation cho từng panel + 1 consolidated
        """
        logger.info(f"Running Multi-Panel QuotationBuilder for {len(state.panels)} panels")
        
        from app.services.export.quotation_builder import QuotationBuilderService
        
        quotation_files = []
        
        # Build quotation cho từng panel
        for panel in state.panels:
            if panel.id == "panel-common":
                continue  # Skip common panel trong per-panel quotations
            
            logger.info(f"Building quotation for panel: {panel.name}")
            
            # Calculate enclosure spec cho panel này
            panel_enclosure = self._calculate_panel_enclosure(panel)
            
            # Build quotation rows
            rows = QuotationBuilderService.build_rows_from_template(
                project_name=panel.name,
                devices=panel.devices,
                enclosure_spec=panel_enclosure,
                template=template
            )
            
            state.quotation_rows_by_panel[panel.id] = rows
            
            quotation_files.append({
                "panel_id": panel.id,
                "panel_name": panel.name,
                "filename": f"BaoGia_{self._sanitize_filename(panel.name)}.xlsx",
                "row_count": len(rows),
                "total_value": sum(r.get("thanh_tien", 0) for r in rows if isinstance(r.get("thanh_tien"), (int, float)))
            })
        
        # Build consolidated quotation (tổng hợp)
        logger.info("Building consolidated quotation")
        consolidated_panel = MultiPanelDetector.create_consolidated_panel(
            state.panels,
            project_name
        )
        
        consolidated_enclosure = self._calculate_panel_enclosure(consolidated_panel)
        
        consolidated_rows = QuotationBuilderService.build_rows_from_template(
            project_name=f"{project_name} - TỔNG HỢP",
            devices=consolidated_panel.devices,
            enclosure_spec=consolidated_enclosure,
            template=template
        )
        
        state.quotation_rows = consolidated_rows
        state.quotation_rows_by_panel["consolidated"] = consolidated_rows
        
        quotation_files.append({
            "panel_id": "consolidated",
            "panel_name": f"{project_name} - TỔNG HỢP",
            "filename": f"BaoGia_TongHop_{self._sanitize_filename(project_name)}.xlsx",
            "row_count": len(consolidated_rows),
            "total_value": sum(r.get("thanh_tien", 0) for r in consolidated_rows if isinstance(r.get("thanh_tien"), (int, float)))
        })
        
        state.completed_agents.append(AgentRole.QUOTATION_BUILDER)
        
        logger.info(
            f"Multi-Panel QuotationBuilder generated {len(quotation_files)} quotation files",
            extra={
                "file_count": len(quotation_files),
                "files": quotation_files
            }
        )
        
        return state
    
    def _calculate_panel_enclosure(self, panel: Panel) -> Dict:
        """Calculate enclosure specs cho 1 panel"""
        # Simple estimation based on device count and incomer
        device_count = panel.device_count
        # Incomer rating lấy từ panel hoặc 0 (không tự ý gán 630A giả)
        incomer_rating = float(panel.incomer_rating or 0.0)
        
        # Height based on device count (mỗi device ~150mm)
        height = min(
            CABINET_HEIGHT_MAX_MM,
            max(CABINET_HEIGHT_MIN_MM, CABINET_HEIGHT_BASE_MM + device_count * CABINET_HEIGHT_PER_DEVICE_MM)
        )
        
        # Width based on incomer rating
        if incomer_rating >= CABINET_WIDTH_INCOMER_LARGE_A:
            width = 1200
        elif incomer_rating >= CABINET_WIDTH_INCOMER_MEDIUM_A:
            width = 1000
        elif incomer_rating >= 100:
            width = 800
        else:
            width = 600
        
        # Depth
        depth = CABINET_DEPTH_HEAVY_MM if incomer_rating >= CABINET_WIDTH_INCOMER_MEDIUM_A else CABINET_DEPTH_LIGHT_MM
        
        return {
            "height": height,
            "width": width,
            "depth": depth,
            "thickness": settings.ENCLOSURE_DEFAULT_THICKNESS,
            "plinth_height": settings.ENCLOSURE_DEFAULT_PLINTH_HEIGHT,
            "incomer_rating": incomer_rating
        }
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize panel name cho filename"""
        import re
        # Remove special chars
        sanitized = re.sub(r'[^\w\s-]', '', name)
        sanitized = re.sub(r'[\s]+', '_', sanitized)
        return sanitized[:MAX_FILENAME_LENGTH]
    
    async def _run_cad_generator(
        self,
        state: ExtractionState,
        project_name: str,
        templates: List[Dict]
    ) -> ExtractionState:
        """
        Agent 6: CAD Generator
        Sinh file CAD DXF theo template mẫu có sẵn trong DB
        """
        logger.info(f"Running CADGenerator agent")
        
        from app.services.cad.template_based_generator import TemplateBasedCADGenerator
        
        # Generate CAD commands từ template
        commands = TemplateBasedCADGenerator.generate_from_template(
            project_name=project_name,
            devices=state.devices,
            enclosure_spec=state.enclosure_spec,
            templates=templates
        )
        
        state.cad_commands = commands
        state.completed_agents.append(AgentRole.CAD_GENERATOR)
        
        logger.info(
            f"CADGenerator generated {len(commands)} commands",
            extra={"command_count": len(commands)}
        )
        
        return state
    
    # ===== PROMPT TEMPLATES =====
    
    def _get_vision_extractor_prompt(self) -> str:
        from app.core.prompts import ORCHESTRATOR_VISION_PROMPT_TEMPLATE
        return ORCHESTRATOR_VISION_PROMPT_TEMPLATE
    
    def _get_spec_validator_prompt(self) -> str:
        return """Agent Spec Validator prompt (not used for AI call, pure Python logic)"""
    
    def _get_catalog_matcher_prompt(self) -> str:
        return """Agent Catalog Matcher prompt (not used for AI call, uses DB queries)"""
    
    def _get_quotation_builder_prompt(self) -> str:
        return """Agent Quotation Builder prompt (uses template-based generation)"""
    
    def _get_cad_generator_prompt(self) -> str:
        return """Agent CAD Generator prompt (uses template-based generation)"""
    
    def _get_quality_checker_prompt(self) -> str:
        return """Agent Quality Checker prompt (pure Python scoring logic)"""

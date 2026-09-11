"""
Multi-Panel Detector
Phát hiện nhiều tủ điện/panels/zones trong 1 sơ đồ
"""
import logging
import re
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field

from app.core.logging_config import get_logger
from app.core.config import settings
from app.core.constants import DEFAULT_PROJECT_NAME

logger = get_logger(__name__)


@dataclass
class Panel:
    """Đại diện cho 1 panel/tủ điện"""
    id: str
    name: str
    zone: Optional[str] = None
    location: Optional[str] = None
    devices: List[Dict] = field(default_factory=list)
    incomer_rating: Optional[float] = None
    device_count: int = 0
    confidence: float = 0.9


class MultiPanelDetector:
    """
    Phát hiện và phân chia devices vào các panels khác nhau
    
    Các trường hợp:
    1. Sơ đồ đơn giản: 1 panel duy nhất
    2. Sơ đồ có nhiều tủ: Panel A, Panel B, Panel C
    3. Sơ đồ có zones: Zone 1, Zone 2
    4. Sơ đồ theo tầng: Tầng 1, Tầng 2, Tầng 3
    5. Sơ đồ có blocks: Block/MCC Panel #1, #2, #3
    """
    
    # Pattern keywords để detect panels
    PANEL_KEYWORDS = [
        # Tủ điện
        r'tủ\s*điện\s*([A-Za-z0-9]+)',
        r'tủ\s*([A-Za-z0-9]+)',
        r'panel\s*([A-Za-z0-9#]+)',
        r'mdb\s*([A-Za-z0-9]+)',
        r'db\s*([A-Za-z0-9]+)',
        r'distribution\s*board\s*([A-Za-z0-9]+)',
        
        # Zones
        r'zone\s*([0-9]+)',
        r'khu\s*vực\s*([0-9A-Za-z]+)',
        
        # Tầng
        r'tầng\s*([0-9]+)',
        r'floor\s*([0-9]+)',
        r'f([0-9]+)',
        
        # Blocks
        r'block\s*([A-Za-z0-9#]+)',
        r'khối\s*([A-Za-z0-9]+)',
        
        # MCC
        r'mcc\s*panel\s*([A-Za-z0-9#]+)',
        r'motor\s*control\s*center\s*([A-Za-z0-9#]+)',
    ]
    
    @staticmethod
    def detect_panels(
        devices: List[Dict],
        project_name: str = ""
    ) -> List[Panel]:
        """
        Phát hiện các panels trong danh sách devices
        
        Args:
            devices: List of extracted devices
            project_name: Project name for default panel
        
        Returns:
            List of Panel objects
        """
        logger.info(f"Detecting panels from {len(devices)} devices")
        
        # Step 1: Tìm panel indicators trong device names và notes
        panel_indicators = MultiPanelDetector._extract_panel_indicators(devices)
        
        if len(panel_indicators) == 0:
            # No panel detected → Single panel project
            logger.info("No multiple panels detected, treating as single panel")
            return [MultiPanelDetector._create_single_panel(devices, project_name)]
        
        elif len(panel_indicators) == 1:
            # Only 1 panel mentioned → Single panel
            panel_name = list(panel_indicators.keys())[0]
            logger.info(f"Single panel detected: {panel_name}")
            return [MultiPanelDetector._create_panel(
                panel_id="panel-1",
                panel_name=panel_name,
                devices=devices
            )]
        
        else:
            # Multiple panels → Split devices
            logger.info(f"Multiple panels detected: {len(panel_indicators)} panels")
            return MultiPanelDetector._split_devices_by_panel(
                devices, panel_indicators
            )
    
    @staticmethod
    def _extract_panel_indicators(devices: List[Dict]) -> Dict[str, Set[int]]:
        """
        Extract panel indicators từ device names và notes
        
        Returns:
            Dict[panel_name -> set of device indices]
        """
        indicators = {}
        
        for idx, device in enumerate(devices):
            # Check name
            name = device.get("name", "")
            notes = device.get("notes", "")
            combined_text = f"{name} {notes}".lower()
            
            # Try all patterns
            for pattern in MultiPanelDetector.PANEL_KEYWORDS:
                matches = re.finditer(pattern, combined_text, re.IGNORECASE)
                for match in matches:
                    panel_identifier = match.group(0)
                    # Normalize panel name
                    panel_name = MultiPanelDetector._normalize_panel_name(panel_identifier)
                    
                    if panel_name not in indicators:
                        indicators[panel_name] = set()
                    indicators[panel_name].add(idx)
        
        return indicators
    
    @staticmethod
    def _normalize_panel_name(raw_name: str) -> str:
        """
        Normalize panel name
        
        Examples:
        - "TỦ ĐIỆN A" → "PANEL-A"
        - "Panel #1" → "PANEL-1"
        - "Zone 2" → "ZONE-2"
        - "MCC Panel 3" → "MCC-PANEL-3"
        """
        name = raw_name.upper().strip()
        
        # Replace common words
        replacements = {
            "TỦ ĐIỆN": "PANEL",
            "TỦ": "PANEL",
            "PANEL": "PANEL",
            "KHU VỰC": "ZONE",
            "ZONE": "ZONE",
            "TẦNG": "FLOOR",
            "FLOOR": "FLOOR",
            "BLOCK": "BLOCK",
            "KHỐI": "BLOCK",
            "MCC PANEL": "MCC-PANEL",
            "MOTOR CONTROL CENTER": "MCC"
        }
        
        for old, new in replacements.items():
            name = name.replace(old, new)
        
        # Clean up
        name = re.sub(r'\s+', '-', name)
        name = re.sub(r'[#]+', '', name)
        
        return name
    
    @staticmethod
    def _split_devices_by_panel(
        devices: List[Dict],
        panel_indicators: Dict[str, Set[int]]
    ) -> List[Panel]:
        """
        Split devices vào các panels dựa trên indicators
        """
        panels = []
        assigned_indices = set()
        
        # Create panels từ indicators
        for panel_idx, (panel_name, device_indices) in enumerate(panel_indicators.items()):
            panel_devices = [devices[i] for i in device_indices if i < len(devices)]
            
            if panel_devices:
                panel = MultiPanelDetector._create_panel(
                    panel_id=f"panel-{panel_idx + 1}",
                    panel_name=panel_name,
                    devices=panel_devices
                )
                panels.append(panel)
                assigned_indices.update(device_indices)
        
        # Handle unassigned devices (không thuộc panel nào)
        unassigned_indices = set(range(len(devices))) - assigned_indices
        if unassigned_indices:
            logger.warning(f"Found {len(unassigned_indices)} unassigned devices")
            unassigned_devices = [devices[i] for i in unassigned_indices]
            
            # Create "COMMON" panel for shared devices (đèn báo, quạt, etc.)
            common_panel = MultiPanelDetector._create_panel(
                panel_id="panel-common",
                panel_name="THIẾT BỊ CHUNG",
                devices=unassigned_devices
            )
            panels.append(common_panel)
        
        return panels
    
    @staticmethod
    def _create_single_panel(devices: List[Dict], project_name: str) -> Panel:
        """Create a single panel for simple projects"""
        panel_name = project_name.upper() if project_name else DEFAULT_PROJECT_NAME.upper()
        return MultiPanelDetector._create_panel(
            panel_id="panel-1",
            panel_name=panel_name,
            devices=devices
        )
    
    @staticmethod
    def _create_panel(panel_id: str, panel_name: str, devices: List[Dict]) -> Panel:
        """Create Panel object with calculated properties"""
        # Find incomer
        incomer = next(
            (d for d in devices if "incomer" in d.get("name", "").lower() or 
             "tổng" in d.get("name", "").lower() or
             d.get("section") == "Đầu vào"),
            None
        )
        
        incomer_rating = incomer.get("in_a") if incomer else None
        
        # Calculate total device count (considering quantity)
        device_count = sum(d.get("quantity", 1) for d in devices)
        
        return Panel(
            id=panel_id,
            name=panel_name,
            devices=devices,
            incomer_rating=incomer_rating,
            device_count=device_count,
            confidence=settings.DEFAULT_CONFIDENCE
        )
    
    @staticmethod
    def create_consolidated_panel(panels: List[Panel], project_name: str) -> Panel:
        """
        Tạo panel tổng hợp (consolidated) từ nhiều panels
        
        Use case: Báo giá tổng cho toàn bộ dự án
        """
        all_devices = []
        for panel in panels:
            all_devices.extend(panel.devices)
        
        # Tính tổng incomer rating
        total_incomer = sum(p.incomer_rating for p in panels if p.incomer_rating)
        
        return Panel(
            id="panel-consolidated",
            name=f"{project_name or DEFAULT_PROJECT_NAME} - TỔNG HỢP",
            devices=all_devices,
            incomer_rating=total_incomer if total_incomer > 0 else None,
            device_count=sum(p.device_count for p in panels),
            confidence=settings.DEFAULT_CONFIDENCE
        )

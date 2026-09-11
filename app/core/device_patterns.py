"""
Advanced regex patterns cho device extraction từ text/CAD/PDF
"""
import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from app.core.constants import DeviceCategory, DEVICE_POLES_MAP

logger = logging.getLogger(__name__)


@dataclass
class DeviceMatch:
    """Kết quả match device từ text"""
    category: str
    poles: Optional[int] = None
    in_a: Optional[float] = None
    icu_ka: Optional[float] = None
    voltage: Optional[int] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    raw_text: str = ""
    confidence: float = 0.85


class DevicePatterns:
    """
    Advanced regex patterns cho device extraction
    Hỗ trợ nhiều format khác nhau, case-insensitive, unicode
    """
    
    # Core patterns - flexible và reusable
    CURRENT = r"(\d+(?:\.\d+)?)\s*[AaАΑ]"  # Support A, a, А (Cyrillic), Α (Greek)
    ICU = r"(\d+(?:\.\d+)?)\s*[Kk][AaАΑ]"
    POLES = r"([1-4])\s*[PpΦфPП]"  # Support P, p, Φ, ф, П
    VOLTAGE = r"(\d+)\s*[VvВ](?:\s*(?:AC|DC|ac|dc))?"
    
    # Separators - allow various formats
    SEP = r"[\s\-_/,.:;]*"  # Space, dash, underscore, slash, comma, colon, semicolon
    OPT_SEP = r"[\s\-_/,.:;]?"  # Optional separator
    
    # Generic breaker parameter token (supports any order of poles, current, icu, incomer)
    BREAKER_PARAM = r"(?:" + ICU + r"|" + POLES + r"|" + CURRENT + r"|(?:tổng|tong|incomer|main))"

    # Device type patterns - case insensitive, support typos & flexible order
    ACB_PATTERN = re.compile(
        r"\b(ACB|A\.C\.B|Air[\s\-]?Circuit[\s\-]?Breaker)(?:" + SEP + BREAKER_PARAM + r"){0,5}",
        re.IGNORECASE
    )
    
    MCCB_PATTERN = re.compile(
        r"\b(MCCB|M\.C\.C\.B|Molded[\s\-]?Case|Aptomat)(?:" + SEP + BREAKER_PARAM + r"){0,5}",
        re.IGNORECASE
    )
    
    MCB_PATTERN = re.compile(
        r"\b(MCB|M\.C\.B|Miniature|Mini[\s\-]?breaker)(?:" + SEP + BREAKER_PARAM + r"){0,5}",
        re.IGNORECASE
    )
    
    RCBO_PATTERN = re.compile(
        r"\b(RCBO|R\.C\.B\.O|Residual.*Overcurrent)(?:" + SEP + BREAKER_PARAM + r"){0,5}",
        re.IGNORECASE
    )
    
    CONTACTOR_PATTERN = re.compile(
        r"\b(Contactor|Khởi[\s\-]?động|Tiếp[\s\-]?xúc)" + SEP +
        r"(?:" + POLES + SEP + r")?" +
        r"(?:" + CURRENT + SEP + r")?" +
        r"(?:coil" + SEP + r"(?:" + VOLTAGE + r"))?",  # Coil voltage
        re.IGNORECASE
    )
    
    METER_PATTERN = re.compile(
        r"\b(Meter|Đồng[\s\-]?hồ|MFM|Power[\s\-]?meter|Multi[\s\-]?function)" + SEP +
        r"(?:(đo|measurement|monitoring))?" + SEP +
        r"(?:" + POLES + SEP + r"pha)?",
        re.IGNORECASE
    )
    
    LIGHT_PATTERN = re.compile(
        r"\b(?:Pilot[\s\-]?light|(?:Đèn|Light|LED)" + SEP +
        r"(?:báo|signal|indicator|chỉ[\s\-]?thị|pha|phase|R[\-\/]?S[\-\/]?T|nguồn|tủ)" + SEP +
        r"(?:pha|phase|R[\-\/]?S[\-\/]?T|đỏ[\-\/]?vàng[\-\/]?xanh|nguồn|tủ)?" + SEP +
        r"(?:phi|Φ|diameter)?\s*(\d+)?)",
        re.IGNORECASE
    )
    
    COOLING_PATTERN = re.compile(
        r"\b(Quạt|Fan|Cooling|Ventilator|Thông[\s\-]?gió)" + SEP +
        r"(?:(làm[\s\-]?mát|cooling|exhaust))?" + SEP +
        r"(?:" + VOLTAGE + r")?",
        re.IGNORECASE
    )
    
    CT_PATTERN = re.compile(
        r"\b(CT|C\.T|Current[\s\-]?Transformer|Biến[\s\-]?dòng)" + SEP +
        r"(?:(\d+)/(\d+))?" + SEP +  # Ratio like 100/5
        r"(?:Class" + SEP + r"([\d\.]+))?",  # Accuracy class
        re.IGNORECASE
    )
    
    SWITCH_PATTERN = re.compile(
        r"\b(Switch|Chuyển[\s\-]?mạch|Selector|Changeover)" + SEP +
        r"(?:" + POLES + SEP + r")?" +
        r"(?:(\d+)[\s\-]?position)?",  # 2-position, 3-position
        re.IGNORECASE
    )
    
    FUSE_PATTERN = re.compile(
        r"\b(Fuse|Cầu[\s\-]?chì|Fu)" + SEP +
        r"(?:(điều[\s\-]?khiển|control|main))?" + SEP +
        r"(?:" + CURRENT + r")?",
        re.IGNORECASE
    )
    
    # Brand patterns
    BRAND_PATTERN = re.compile(
        r"\b(LS|Schneider|ABB|Siemens|Mitsubishi|Fuji|Terasaki|Hyundai|"
        r"Simon|Morele|Idec|Selec|Leipole|Hager|Legrand)" + 
        r"(?:\s*Electric)?",
        re.IGNORECASE
    )
    
    # Comprehensive extraction pattern - tries to match device with all attributes in one go
    COMPREHENSIVE_PATTERN = re.compile(
        r"(ACB|MCCB|MCB|RCBO|RCCB|Contactor|CT|Aptomat|Khởi[\s\-]?động)" + SEP +
        r"(?:(tổng|main|incomer))?" + SEP +
        r"(?:([1-4])\s*[PpΦфPП])?" + SEP +
        r"(?:(\d+(?:\.\d+)?)\s*[AaАΑ])?" + SEP +
        r"(?:(\d+(?:\.\d+)?)\s*[Kk][AaАΑ])?",
        re.IGNORECASE
    )
    
    @classmethod
    def extract_all_devices(cls, text: str) -> List[DeviceMatch]:
        """
        Extract tất cả devices từ text sử dụng tất cả patterns
        
        Args:
            text: Input text (từ PDF, CAD label, etc.)
            
        Returns:
            List of DeviceMatch objects
        """
        if not text or not text.strip():
            return []
        
        devices = []
        
        # Try each pattern type
        devices.extend(cls._extract_with_pattern(text, cls.ACB_PATTERN, "ACB", 0.95))
        devices.extend(cls._extract_with_pattern(text, cls.MCCB_PATTERN, "MCCB", 0.92))
        devices.extend(cls._extract_with_pattern(text, cls.MCB_PATTERN, "MCB", 0.90))
        devices.extend(cls._extract_with_pattern(text, cls.RCBO_PATTERN, "RCBO", 0.90))
        devices.extend(cls._extract_with_pattern(text, cls.CONTACTOR_PATTERN, "CONTACTOR", 0.88))
        devices.extend(cls._extract_with_pattern(text, cls.METER_PATTERN, "METER", 0.85))
        devices.extend(cls._extract_with_pattern(text, cls.LIGHT_PATTERN, "LIGHT", 0.85))
        devices.extend(cls._extract_with_pattern(text, cls.COOLING_PATTERN, "COOLING", 0.85))
        devices.extend(cls._extract_with_pattern(text, cls.CT_PATTERN, "CT", 0.88))
        devices.extend(cls._extract_with_pattern(text, cls.SWITCH_PATTERN, "SWITCH", 0.85))
        devices.extend(cls._extract_with_pattern(text, cls.FUSE_PATTERN, "FUSE", 0.85))
        
        # Deduplicate based on position overlap
        devices = cls._deduplicate_overlapping(devices)
        
        logger.info(f"Extracted {len(devices)} devices from text (length: {len(text)})")
        return devices
    
    @classmethod
    def _extract_with_pattern(
        cls,
        text: str,
        pattern: re.Pattern,
        category: str,
        base_confidence: float
    ) -> List[DeviceMatch]:
        """Extract devices using a specific pattern"""
        devices = []
        
        for match in pattern.finditer(text):
            try:
                device = cls._parse_match(match, category, base_confidence)
                if device:
                    devices.append(device)
            except Exception as e:
                logger.warning(f"Failed to parse match for {category}: {str(e)}")
                continue
        
        return devices
    
    @classmethod
    def _parse_match(
        cls,
        match: re.Match,
        category: str,
        base_confidence: float
    ) -> Optional[DeviceMatch]:
        """Parse regex match into DeviceMatch object"""
        groups = match.groups()
        raw_text = match.group(0)
        
        # Extract attributes from groups
        poles = None
        in_a = None
        icu_ka = None
        voltage = None
        brand = None
        
        # Try to find poles in the matched text
        poles_match = re.search(cls.POLES, raw_text)
        if poles_match:
            poles = int(poles_match.group(1))
        
        # Try to find current rating
        current_match = re.search(cls.CURRENT, raw_text)
        if current_match:
            in_a = float(current_match.group(1))
        
        # Try to find Icu
        icu_match = re.search(cls.ICU, raw_text)
        if icu_match:
            icu_ka = float(icu_match.group(1))
        
        # Try to find voltage
        voltage_match = re.search(cls.VOLTAGE, raw_text)
        if voltage_match:
            voltage = int(voltage_match.group(1))
        
        # Try to find brand
        brand_match = cls.BRAND_PATTERN.search(raw_text)
        if brand_match:
            brand = brand_match.group(1)
        
        # Adjust confidence based on how much info we extracted
        confidence = base_confidence
        if in_a:
            confidence += 0.03
        if icu_ka:
            confidence += 0.02
        if poles:
            confidence += 0.02
        confidence = min(confidence, 0.99)
        
        return DeviceMatch(
            category=category,
            poles=poles,
            in_a=in_a,
            icu_ka=icu_ka,
            voltage=voltage,
            brand=brand,
            raw_text=raw_text,
            confidence=confidence
        )
    
    @classmethod
    def _deduplicate_overlapping(cls, devices: List[DeviceMatch]) -> List[DeviceMatch]:
        """
        Remove overlapping matches, keeping the one with higher confidence
        Two matches overlap if their raw_text positions overlap significantly
        """
        if len(devices) <= 1:
            return devices
        
        # Sort by confidence descending
        sorted_devices = sorted(devices, key=lambda d: d.confidence, reverse=True)
        
        result = []
        used_texts = set()
        
        for device in sorted_devices:
            # Simple deduplication by exact text match
            if device.raw_text not in used_texts:
                result.append(device)
                used_texts.add(device.raw_text)
        
        return result
    
    @classmethod
    def extract_from_panel_schedule(cls, text: str) -> List[DeviceMatch]:
        """
        Extract devices từ panel schedule format
        Ví dụ:
        - Circuit 1: MCB 3P 20A 6kA
        - Feeder 2: MCCB 3P 250A 30kA
        """
        devices = []
        
        # Pattern for panel schedule lines
        schedule_pattern = re.compile(
            r"(?:Circuit|Feeder|Line|Lộ|Nhánh)\s*(\d+)[\s:,\-]+" +
            r"(ACB|MCCB|MCB|RCBO)" + cls.SEP +
            r"(?:([1-4])[PpΦ])?" + cls.SEP +
            r"(\d+)[AaАΑ]" + cls.SEP +
            r"(?:(\d+)[Kk][AaАΑ])?",
            re.IGNORECASE
        )
        
        for match in schedule_pattern.finditer(text):
            circuit_num = match.group(1)
            category = match.group(2).upper()
            poles = int(match.group(3)) if match.group(3) else None
            in_a = float(match.group(4))
            icu_ka = float(match.group(5)) if match.group(5) else None
            
            devices.append(DeviceMatch(
                category=category,
                poles=poles,
                in_a=in_a,
                icu_ka=icu_ka,
                raw_text=match.group(0),
                confidence=0.95
            ))
        
        return devices
    
    @classmethod
    def normalize_brand_name(cls, brand: Optional[str]) -> str:
        """Normalize brand name to standard format"""
        if not brand:
            return ""
        
        brand_lower = brand.lower().strip()
        
        # Check aliases from constants
        from app.core.constants import BRAND_ALIASES
        for standard, aliases in BRAND_ALIASES.items():
            if brand_lower in aliases:
                return standard.upper()
        
        return brand.upper()


# Convenience function
def extract_devices_from_text(text: str) -> List[DeviceMatch]:
    """Quick extraction from text"""
    return DevicePatterns.extract_all_devices(text)

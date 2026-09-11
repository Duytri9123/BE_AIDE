"""
Application constants và enums
"""
from enum import Enum


class DeviceCategory(str, Enum):
    """Loại thiết bị điện"""
    ACB = "ACB"  # Air Circuit Breaker
    MCCB = "MCCB"  # Molded Case Circuit Breaker
    MCB = "MCB"  # Miniature Circuit Breaker
    RCBO = "RCBO"  # Residual Current Breaker with Overcurrent
    RCCB = "RCCB"  # Residual Current Circuit Breaker
    CONTACTOR = "CONTACTOR"
    RELAY = "RELAY"
    METER = "METER"  # Đồng hồ đo
    LIGHT = "LIGHT"  # Đèn báo
    SWITCH = "SWITCH"  # Chuyển mạch
    FUSE = "FUSE"  # Cầu chì
    COOLING = "COOLING"  # Quạt/làm mát
    BUTTON = "BUTTON"  # Nút nhấn
    CAPACITOR = "CAPACITOR"  # Tụ bù
    CT = "CT"  # Current Transformer
    OTHER = "OTHER"


class DeviceSection(str, Enum):
    """Khu vực chức năng trong tủ điện"""
    INCOMER = "Đầu vào"  # Incomer section
    FEEDER = "Đầu ra"  # Outgoing feeders
    METERING = "Đo lường & Giám sát"
    CONTROL = "Điều khiển & Chiếu sáng"
    COMPENSATION = "Bù công suất"
    COOLING = "Làm mát cho ngăn tủ"
    OTHER = "Khác"


class FileFormat(str, Enum):
    """Supported file formats"""
    # Images
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    WEBP = "webp"
    BMP = "bmp"
    
    # CAD
    DXF = "dxf"
    DWG = "dwg"
    
    # Documents
    PDF = "pdf"


class AIProvider(str, Enum):
    """AI Vision providers"""
    OPENAI = "openai"
    GEMINI = "gemini"
    GOOGLE = "google"
    ANTIGRAVITY = "antigravity"
    CLAUDE = "claude"


class ExportFormat(str, Enum):
    """Export file formats"""
    EXCEL = "xlsx"
    PDF = "pdf"
    DXF = "dxf"
    CSV = "csv"
    JSON = "json"


class EnclosureType(str, Enum):
    """Loại vỏ tủ điện"""
    INDOOR = "Indoor"  # Tủ trong nhà
    OUTDOOR = "Outdoor"  # Tủ ngoài trời
    WALL_MOUNTED = "Wall Mounted"  # Tủ treo tường
    FLOOR_STANDING = "Floor Standing"  # Tủ đứng sàn


class BusbarMaterial(str, Enum):
    """Vật liệu thanh cái"""
    COPPER = "Cu"  # Đồng
    ALUMINUM = "Al"  # Nhôm


class QuotationRowType(str, Enum):
    """Loại dòng trong bảng báo giá"""
    PANEL_HEADER = "panel_header"
    SECTION_HEADER = "section_header"
    ITEM = "item"
    SUBTOTAL = "subtotal"
    TOTAL = "total"


# Device specifications
DEVICE_POLES_MAP = {
    "1P": 1,
    "2P": 2,
    "3P": 3,
    "4P": 4,
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
}

# Brand mappings (normalize brand names)
BRAND_ALIASES = {
    "ls": ["ls electric", "ls", "lg", "lg electric"],
    "schneider": ["schneider electric", "schneider", "se"],
    "abb": ["abb", "asea brown boveri"],
    "siemens": ["siemens", "sie"],
    "mitsubishi": ["mitsubishi electric", "mitsubishi", "mee"],
    "fuji": ["fuji electric", "fuji"],
    "terasaki": ["terasaki", "tera"],
    "hyundai": ["hyundai", "hd"],
}

# Common regex patterns
PATTERNS = {
    "current_rating": r"(\d+(?:\.\d+)?)\s*[Aa]",  # 100A, 630a, 25.5A
    "icu_rating": r"(\d+(?:\.\d+)?)\s*[Kk][Aa]",  # 45kA, 36KA
    "poles": r"([1-4])\s*[PpΦф]",  # 3P, 2p, 3Φ, 4ф
    "voltage": r"(\d+)\s*[Vv](?:AC|DC)?",  # 220V, 400VAC, 24VDC
}

# Bảng map thương hiệu hiển thị với key catalog trong hệ thống
BRAND_CATALOG_MAPPING = {
    "Schneider Electric": "schneider",
    "Schneider": "schneider",
    "LS Electric": "ls_standard",
    "LS Electric Premium": "ls_premium",
    "Mitsubishi": "mitsubishi",
    "ABB": "abb",
    "Chint": "chint",
    "Emic": "emic",
    "Samwha": "samwha",
    "Shihlin Electric": "shihlin",
    "Siemens": "siemens",
    "Fuji Electric": "fuji",
    "Hyundai Electric": "hyundai",
    "Hyundai": "hyundai",
    "Terasaki": "terasaki",
    "Panasonic": "panasonic",
}


# =============================================================================
# Busbar Engineering Constants
# =============================================================================

# Ngưỡng dòng điện để xác định cần thanh cái
BUSBAR_REQUIRED_MIN_CURRENT_A: float = 100.0   # Tủ ≥100A phải có thanh cái
BUSBAR_MIN_INCOMER_CURRENT_A: float = 40.0     # Dòng incomer tối thiểu để tính toán

# Hệ số chiều dài thanh cái chính (3L + N(100%) + PE(50%) = 4.5×W_tủ)
BUSBAR_PHASE_MULTIPLIER: float = 4.5

# Chiều dài dropper nhánh tính theo số cực
BUSBAR_DROPPER_LENGTH_PER_POLE_M: float = 0.4  # m/cực
BUSBAR_MIN_DROPPER_LENGTH_M: float = 1.0        # m (tối thiểu)

# Hệ số hao hụt vật liệu khi uốn/đột/gia công
BUSBAR_WASTE_FACTOR: float = 1.05

# Tỷ trọng đồng: 8.9 g/cm³ → 8.9e-3 kg/(m·mm²)
COPPER_DENSITY_KG_PER_M_MM2: float = 8.9e-3

# Khoảng cách đặt sứ đỡ thanh cái
BUSBAR_INSULATOR_SPACING_M: float = 0.5        # 500 mm/sứ

# Đơn giá sứ đỡ SM-40
BUSBAR_INSULATOR_PRICE_VND: int = 12000

# Bảng mật độ dòng điện thanh cái theo cấp dòng (A/mm²)
# Key = ngưỡng dòng tối đa (A), Value = mật độ (A/mm²)
BUSBAR_CURRENT_DENSITY_TABLE = {
    400: 2.0,           # In ≤ 400A → J = 2.0 A/mm²
    1000: 1.8,          # 400 < In ≤ 1000A → J = 1.8 A/mm²
    float("inf"): 1.5,  # In > 1000A → J = 1.5 A/mm²
}

# =============================================================================
# Enclosure Engineering Constants
# =============================================================================

# Tỷ trọng thép CT3 sơn tĩnh điện
STEEL_DENSITY_G_CM3: float = 7.85              # g/cm³

# Ngưỡng chiều cao để phân loại tủ đứng sàn vs tủ treo tường
FLOOR_STANDING_HEIGHT_THRESHOLD_MM: int = 1200  # mm

# Bước làm tròn giá (đồng bộ mọi nơi dùng làm tròn 50K VNĐ)
PRICE_ROUNDING_STEP_VND: int = 50000

# Cabinet sizing — height estimation
CABINET_HEIGHT_BASE_MM: int = 800              # Chiều cao cơ bản (mm)
CABINET_HEIGHT_PER_DEVICE_MM: int = 150        # Tăng thêm mỗi thiết bị (mm)
CABINET_HEIGHT_MIN_MM: int = 1200              # Chiều cao tối thiểu (mm)
CABINET_HEIGHT_MAX_MM: int = 2400              # Chiều cao tối đa (mm)

# Cabinet sizing — depth estimation theo incomer
CABINET_DEPTH_HEAVY_MM: int = 600              # Depth khi incomer ≥ 400A
CABINET_DEPTH_LIGHT_MM: int = 500              # Depth khi incomer < 400A

# Ngưỡng incomer để xác định width tủ
CABINET_WIDTH_INCOMER_LARGE_A: int = 1000      # ≥ 1000A → width 1200mm
CABINET_WIDTH_INCOMER_MEDIUM_A: int = 400      # ≥ 400A → width 1000mm
# < 400A → width 800mm

# =============================================================================
# Accessories Unit Prices (VNĐ)
# =============================================================================

COSSE_UNIT_PRICE_VND: int = 2000               # Đầu cosse đồng các loại (VNĐ/cái)
CABLE_DUCT_PRICE_VND_PER_M: int = 45000        # Máng cáp nhựa 60×60mm (VNĐ/m)
DIN_RAIL_PRICE_VND_PER_M: int = 25000          # Thanh ray nhôm C35 (VNĐ/m)
DIN_RAIL_WASTE_FACTOR: float = 1.25            # Hệ số hao hụt cắt lắp DIN rail

# =============================================================================
# Complexity Classification Thresholds (Multi-Agent Orchestrator)
# =============================================================================

COMPLEXITY_SIMPLE_MAX_DEVICES: int = 3         # ≤ 3 thiết bị → SIMPLE
COMPLEXITY_STANDARD_MAX_DEVICES: int = 10      # ≤ 10 thiết bị → STANDARD
COMPLEXITY_COMPLEX_MAX_DEVICES: int = 30       # ≤ 30 thiết bị → COMPLEX
# > 30 thiết bị → VERY_COMPLEX

# =============================================================================
# File & Filename Constants
# =============================================================================

MAX_FILENAME_LENGTH: int = 50                  # Giới hạn độ dài tên file xuất
DEFAULT_PROJECT_NAME: str = "Tu_Dien"           # Tên dự án mặc định khi không xác định
DEFAULT_PANEL_CODE: str = "CHUA_XAC_DINH"       # Sentinel rõ ràng, không giả làm mã đọc từ bản vẽ

import json
from typing import List, Union, Optional
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "BE_BOM"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str
    DB_ECHO: bool = False

    @property
    def DATABASE_ASYNC_URL(self) -> str:
        # Đảm bảo sử dụng async driver cho async SQLAlchemy
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        if self.DATABASE_URL.startswith("mysql://"):
            return self.DATABASE_URL.replace("mysql://", "mysql+aiomysql://")
        return self.DATABASE_URL

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 ngày (7 * 24 * 60 phút)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None


    # Redis / Celery
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    CELERY_BROKER_URL: str = "redis://127.0.0.1:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://127.0.0.1:6379/1"

    # Qdrant
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = []

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v

    # AI Providers
    DEFAULT_AI_PROVIDER: str = "gemini"
    AI_CONNECTION_TEST_PROMPT: str = "Xin chào! Hãy xác nhận kết nối bằng tiếng Việt ngắn gọn trong 1 câu: 1+1 bằng mấy?"
    AI_COMPATIBLE_DEFAULT_BASE_URL: str = "https://api.openai.com/v1"

    # File Storage
    UPLOAD_DIR: str = "storage/uploads"
    PROJECTS_DIR: str = "storage/projects"
    USER_LIBRARY_DIR: str = "storage/user_library"
    EXPORT_DIR: str = "storage/exports"
    MAX_FILE_SIZE_MB: int = 50
    
    # Quotation & General Defaults
    DEFAULT_VAT_RATE: float = 0.08  # Mặc định VAT 8% (linh hoạt tùy biến 10% theo yêu cầu)
    DEFAULT_BRAND: str = "Theo thiết kế"  # Ưu tiên bảo toàn hãng bóc tách từ bản vẽ

    # Busbar & Enclosure Engineering Pricing Defaults
    BUSBAR_PRICE_PER_KG: float = 280000.0  # VNĐ / kg đồng mạ thiếc co nhiệt gia công
    BUSBAR_MIN_PRICE: int = 800000         # VNĐ tối thiểu cho hệ thanh cái
    ENCLOSURE_MIN_PRICE: int = 1200000     # VNĐ tối thiểu cho vỏ tủ
    ENCLOSURE_TOLE_PRICE_PER_KG: float = 45000.0  # VNĐ / kg tole sơn tĩnh điện
    ENCLOSURE_BASE_FABRICATION_FEE: float = 500000.0 # Chi phí chấn gấp đột CNC cơ bản
    ACCESSORY_BUSBAR_DEFAULT_PRICE: int = 0   # Vật tư phụ tủ có thanh cái (0: ưu tiên tính theo định mức thiết bị thực tế)
    ACCESSORY_NON_BUSBAR_DEFAULT_PRICE: int = 0 # Vật tư phụ tủ nhỏ không thanh cái
    LABOR_BUSBAR_DEFAULT_COST: int = 0         # Nhân công tủ có thanh cái (0: ưu tiên tính theo định mức kỹ thuật)
    LABOR_NON_BUSBAR_DEFAULT_COST: int = 0      # Nhân công tủ nhỏ không thanh cái
    
    # BOM Extraction Settings
    # Supported file formats
    SUPPORTED_IMAGE_FORMATS: List[str] = ["png", "jpg", "jpeg", "webp", "bmp"]
    SUPPORTED_CAD_FORMATS: List[str] = ["dxf", "dwg"]
    SUPPORTED_PDF_FORMATS: List[str] = ["pdf"]
    
    # AI Vision Settings
    # Timeout 120s đảm bảo AI Vision có đủ thời gian đọc bản vẽ sơ đồ 1 sợi và sinh JSON chi tiết
    AI_VISION_TIMEOUT: int = 120  # seconds
    AI_VISION_MAX_RETRIES: int = 3
    AI_VISION_RETRY_BACKOFF: int = 2  # seconds
    AI_MAX_OUTPUT_TOKENS: int = 32768  # Tăng lên 32768 để xuất đầy đủ thiết bị bản vẽ lớn không bị cắt cụt JSON
    # Thứ tự ưu tiên hãng mặc định (có thể override qua .env)
    DEFAULT_BRAND_PRIORITY_GENERAL: str = "Schneider Electric,LS Electric,Mitsubishi,ABB,Chint"
    DEFAULT_BRAND_PRIORITY_ACB: str = "ABB,Schneider Electric,Mitsubishi,LS Electric,Chint"
    DEFAULT_BRAND_PRIORITY_MCCB: str = "Schneider Electric,ABB,Mitsubishi,LS Electric,Chint"
    DEFAULT_BRAND_PRIORITY_RCBO: str = "Chint,ABB,Mitsubishi,Schneider Electric,LS Electric"
    
    # Token Estimation Settings
    TOKEN_BASE_COST: int = 500  # Base cost per analysis
    TOKEN_PER_DEVICE: int = 150  # Cost per device extracted
    TOKEN_PER_1K_CHARS: int = 4  # Approximate tokens per 1000 characters (GPT-4 ratio)
    
    # Device Defaults (Không ép giá trị giả - ưu tiên dữ liệu từ bản vẽ/AI/catalog)
    DEFAULT_INCOMER_RATING: Optional[int] = None  # None: không tự bịa 630A, xác định từ thiết bị thực tế
    DEFAULT_ICU_KA: Optional[float] = None        # None: không tự bịa 45kA
    DEFAULT_POLES: Optional[int] = None           # None: không tự bịa 3P
    DEFAULT_CONFIDENCE: float = 0.0               # 0.0: không tự gán 0.95 giả
    
    # Device Validation Limits
    MIN_CURRENT_RATING: float = 1.0  # Amperes
    MAX_CURRENT_RATING: float = 10000.0  # Amperes
    MIN_ICU_KA: float = 0.1
    MAX_ICU_KA: float = 200.0
    VALID_POLES: List[int] = [1, 2, 3, 4]
    
    # Enclosure Calculation Defaults
    ENCLOSURE_DEFAULT_THICKNESS: int = 2  # mm
    ENCLOSURE_DEFAULT_PLINTH_HEIGHT: int = 200  # mm
    ENCLOSURE_MIN_WIDTH: int = 400  # mm
    ENCLOSURE_MIN_HEIGHT: int = 600  # mm
    ENCLOSURE_MIN_DEPTH: int = 300  # mm
    
    # Labor Calculation Settings
    DEFAULT_LABOR_HOURLY_RATE: float = 150000.0  # VNĐ / giờ công cơ điện chuẩn

    # Labor Estimation Rates — hệ số nhân công gia công tủ điện (có thể override qua .env)
    LABOR_RATE_SHEET_METAL_H_PER_M2: float = 2.5   # Giờ công/m² tole chấn gấp CNC
    LABOR_RATE_MOUNTING_H_PER_DEVICE: float = 0.4  # Giờ công lắp đặt/thiết bị
    LABOR_RATE_BUSBAR_H_PER_KG: float = 0.8        # Giờ công gia công đồng/kg
    LABOR_RATE_WIRING_H_PER_DEVICE: float = 0.5    # Giờ công đấu nối/thiết bị
    LABOR_RATE_TESTING_H_PER_DEVICE: float = 0.2   # Giờ công kiểm tra/thiết bị
    LABOR_TESTING_BASE_HOURS: float = 4.0           # Giờ base kiểm tra xuất xưởng
    WORK_HOURS_PER_DAY: float = 8.0                 # Số giờ/ngày công tiêu chuẩn

    # Protection Check Settings
    PROTECTION_SIMULTANEITY_FACTOR: float = 0.8  # Hệ số đồng thời K (IEC 60364 / TCVN)

    # Multi-Agent Orchestrator Settings
    ORCHESTRATOR_MAX_ITERATIONS: int = 5           # Số vòng lặp tối đa
    ORCHESTRATOR_CONFIDENCE_THRESHOLD: float = 0.90  # Ngưỡng confidence để dừng
    
    # Busbar Calculation Settings
    BUSBAR_CU_RESISTIVITY: float = 0.0175  # Ω·mm²/m at 20°C
    BUSBAR_TEMP_COEFFICIENT: float = 0.00393  # per °C
    BUSBAR_CURRENT_DENSITY: float = 1.0  # A/mm² (1mm = 2A rule)
    BUSBAR_NEUTRAL_RATIO: float = 0.5  # N = 50% of phase
    BUSBAR_EARTH_RATIO: float = 0.25  # E = 25% of phase
    
    # PDF Extraction Settings
    PDF_MAX_PAGES: int = 100
    PDF_TEXT_ENCODING: str = "utf-8"
    
    # CAD Extraction Settings
    CAD_DXF_ENCODING: str = "utf-8"
    CAD_DEFAULT_UNITS: str = "mm"
    
    # Catalog Matching Settings
    CATALOG_MATCH_THRESHOLD: float = 0.8  # Similarity threshold for fuzzy matching
    CATALOG_MAX_RESULTS: int = 5
    
    # Export Settings
    EXPORT_DIR: str = "storage/exports"
    EXPORT_DXF_VERSION: str = "R2018"  # AutoCAD version
    EXPORT_EXCEL_ENGINE: str = "openpyxl"
    
    # Logging Settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text
    LOG_FILE: str = "logs/bom_extraction.log"
    LOG_MAX_BYTES: int = 10485760  # 10MB
    LOG_BACKUP_COUNT: int = 5

    # Pusher Realtime Configuration (Không dùng mock credentials mặc định)
    PUSHER_APP_ID: Optional[str] = None
    PUSHER_KEY: Optional[str] = None
    PUSHER_SECRET: Optional[str] = None
    PUSHER_CLUSTER: str = "ap1"
    PUSHER_CHANNEL: str = "aide-admin-channel"
    PUSHER_SSL: bool = True

    # SePay Payment Gateway Configuration
    SEPAY_API_KEY: Optional[str] = None
    SEPAY_BANK_NAME: str = "MBBank"
    SEPAY_ACCOUNT_NUMBER: str = "0388888888"
    SEPAY_ACCOUNT_NAME: str = "DGP ELECTRIC"

    # Google AdSense & Ad Gate
    GOOGLE_ADSENSE_CLIENT_ID: str = ""   # ca-pub-XXXXXXXXXXXXXXXX
    GOOGLE_ADSENSE_SLOT_ID: str = ""     # Ad slot ID
    AD_ENABLED: bool = True              # Bật/tắt quảng cáo
    AD_FREQUENCY: int = 5               # Số file tải giữa 2 lần xem quảng cáo

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

settings = Settings()

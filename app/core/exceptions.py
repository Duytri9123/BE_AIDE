"""
Custom exceptions cho hệ thống bóc tách BOM
"""
from typing import Optional


class BOMExtractionError(Exception):
    """Base exception cho tất cả lỗi liên quan đến BOM extraction"""
    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class AIVisionError(BOMExtractionError):
    """Lỗi khi gọi AI Vision API"""
    pass


class AITimeoutError(AIVisionError):
    """Lỗi timeout khi gọi AI API"""
    pass


class AIRateLimitError(AIVisionError):
    """Lỗi rate limit từ AI provider"""
    pass


class AIAuthenticationError(AIVisionError):
    """Lỗi xác thực API key không hợp lệ"""
    pass


class PDFParsingError(BOMExtractionError):
    """Lỗi khi parse file PDF"""
    pass


class CADParsingError(BOMExtractionError):
    """Lỗi khi parse file CAD (DXF/DWG)"""
    pass


class ImageParsingError(BOMExtractionError):
    """Lỗi khi xử lý file hình ảnh"""
    pass


class DeviceValidationError(BOMExtractionError):
    """Lỗi validation dữ liệu thiết bị"""
    pass


class FileNotFoundError(BOMExtractionError):
    """File không tồn tại hoặc không thể truy cập"""
    pass


class FileSizeExceededError(BOMExtractionError):
    """File vượt quá kích thước cho phép"""
    pass


class UnsupportedFileFormatError(BOMExtractionError):
    """Định dạng file không được hỗ trợ"""
    pass


class CatalogMatchError(BOMExtractionError):
    """Lỗi khi khớp thiết bị với catalog"""
    pass


class TokenLimitExceededError(BOMExtractionError):
    """User không đủ token để thực hiện phân tích"""
    pass


class ResponseParsingError(BOMExtractionError):
    """Lỗi khi parse response từ AI"""
    pass

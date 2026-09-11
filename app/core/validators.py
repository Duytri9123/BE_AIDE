"""
Input/Output validation utilities
"""
import os
import logging
from pathlib import Path
from typing import Optional, List, Tuple

from app.core.config import settings
from app.core.constants import FileFormat, DeviceCategory
from app.core.exceptions import (
    DeviceValidationError,
    FileSizeExceededError,
    UnsupportedFileFormatError,
    FileNotFoundError as BOMFileNotFoundError
)

logger = logging.getLogger(__name__)


class FileValidator:
    """Validate uploaded files"""
    
    @staticmethod
    def validate_file_exists(file_path: str) -> bool:
        """Check if file exists and is accessible"""
        if not file_path or not file_path.strip():
            raise BOMFileNotFoundError(
                "File path is empty",
                {"path": file_path}
            )
        
        if not os.path.exists(file_path):
            raise BOMFileNotFoundError(
                f"File không tồn tại: {file_path}",
                {"path": file_path}
            )
        
        if not os.path.isfile(file_path):
            raise BOMFileNotFoundError(
                f"Path không phải là file: {file_path}",
                {"path": file_path}
            )
        
        if not os.access(file_path, os.R_OK):
            raise BOMFileNotFoundError(
                f"Không có quyền đọc file: {file_path}",
                {"path": file_path}
            )
        
        return True
    
    @staticmethod
    def validate_file_size(file_path: str) -> int:
        """
        Validate file size within limits
        Returns file size in bytes
        """
        FileValidator.validate_file_exists(file_path)
        
        file_size = os.path.getsize(file_path)
        max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024  # Convert MB to bytes
        
        if file_size > max_size:
            raise FileSizeExceededError(
                f"File quá lớn: {file_size / 1024 / 1024:.2f}MB (max: {settings.MAX_FILE_SIZE_MB}MB)",
                {
                    "path": file_path,
                    "size_bytes": file_size,
                    "size_mb": file_size / 1024 / 1024,
                    "max_mb": settings.MAX_FILE_SIZE_MB
                }
            )
        
        logger.debug(f"File size OK: {file_size / 1024:.2f}KB")
        return file_size
    
    @staticmethod
    def validate_file_format(file_path: str, filename: Optional[str] = None) -> str:
        """
        Validate file format is supported
        Returns the file extension (lowercase)
        """
        if filename:
            ext = filename.split(".")[-1].lower() if "." in filename else ""
        else:
            ext = Path(file_path).suffix.lstrip(".").lower()
        
        if not ext:
            raise UnsupportedFileFormatError(
                "Không xác định được định dạng file",
                {"path": file_path, "filename": filename}
            )
        
        all_supported = (
            settings.SUPPORTED_IMAGE_FORMATS +
            settings.SUPPORTED_CAD_FORMATS +
            settings.SUPPORTED_PDF_FORMATS
        )
        
        if ext not in all_supported:
            raise UnsupportedFileFormatError(
                f"Định dạng file '{ext}' không được hỗ trợ",
                {
                    "path": file_path,
                    "extension": ext,
                    "supported": all_supported
                }
            )
        
        logger.debug(f"File format OK: {ext}")
        return ext
    
    @staticmethod
    def validate_file(file_path: str, filename: Optional[str] = None) -> Tuple[str, int]:
        """
        Complete file validation
        Returns (extension, file_size)
        """
        FileValidator.validate_file_exists(file_path)
        file_size = FileValidator.validate_file_size(file_path)
        ext = FileValidator.validate_file_format(file_path, filename)
        
        logger.info(f"File validation passed: {file_path} ({ext}, {file_size / 1024:.2f}KB)")
        return ext, file_size


class DeviceValidator:
    """Validate device specifications"""
    
    @staticmethod
    def validate_current_rating(in_a: Optional[float]) -> Optional[float]:
        """Validate current rating (In) is within acceptable range"""
        if in_a is None:
            return None
        
        # Thiết bị phụ trợ (đèn báo, đồng hồ, tiếp điểm, phụ kiện) hoặc AI trả về 0.0A -> Chuẩn hóa về None
        if in_a <= 0:
            return None
        
        if in_a < settings.MIN_CURRENT_RATING:
            if in_a >= 0.1:
                return float(in_a)
            return None
        
        if in_a > settings.MAX_CURRENT_RATING:
            logger.warning(f"Current rating vượt ngưỡng: {in_a}A (max: {settings.MAX_CURRENT_RATING}A), tự động giới hạn.")
            return float(settings.MAX_CURRENT_RATING)
        
        return in_a
    
    @staticmethod
    def validate_icu_rating(icu_ka: Optional[float]) -> Optional[float]:
        """Validate short-circuit breaking capacity (Icu)"""
        if icu_ka is None or icu_ka <= 0:
            return None
        
        if icu_ka < settings.MIN_ICU_KA:
            return float(icu_ka) if icu_ka >= 1.0 else None
        
        if icu_ka > settings.MAX_ICU_KA:
            logger.warning(f"Icu rating vượt ngưỡng: {icu_ka}kA (max: {settings.MAX_ICU_KA}kA), tự động giới hạn.")
            return float(settings.MAX_ICU_KA)
        
        return icu_ka
    
    @staticmethod
    def validate_poles(poles: Optional[int]) -> Optional[int]:
        """Validate number of poles"""
        if poles is None:
            return None
        
        try:
            p = int(poles)
            if p in settings.VALID_POLES:
                return p
            # Chuẩn hóa nếu AI trả về số cực khác thường (ví dụ 5 cực cho thanh domino 5P hoặc dây 5C)
            logger.warning(f"Số cực không chuẩn: {poles} (valid: {settings.VALID_POLES}), tự động chuẩn hóa về 4P.")
            if p >= 4:
                return 4
            elif p <= 1:
                return 1
            return None
        except Exception:
            return None
    
    @staticmethod
    def validate_quantity(quantity: int) -> int:
        """Validate device quantity"""
        if quantity <= 0:
            raise DeviceValidationError(
                f"Số lượng phải > 0: {quantity}",
                {"quantity": quantity}
            )
        
        if quantity > 10000:  # Reasonable upper limit
            logger.warning(f"Large quantity detected: {quantity}")
        
        return quantity
    
    @staticmethod
    def validate_confidence(confidence: float) -> float:
        """Validate confidence score"""
        if not 0 <= confidence <= 1:
            raise DeviceValidationError(
                f"Confidence phải trong [0, 1]: {confidence}",
                {"confidence": confidence}
            )
        
        return confidence
    
    @staticmethod
    def validate_device_spec(
        category: str,
        in_a: Optional[float] = None,
        icu_ka: Optional[float] = None,
        poles: Optional[int] = None,
        quantity: int = 1,
        confidence: float = 0.95
    ) -> dict:
        """
        Validate complete device specification
        Returns validated values as dict
        """
        # Validate and normalize
        validated = {
            "category": category.upper() if category else "OTHER",
            "in_a": DeviceValidator.validate_current_rating(in_a),
            "icu_ka": DeviceValidator.validate_icu_rating(icu_ka),
            "poles": DeviceValidator.validate_poles(poles),
            "quantity": DeviceValidator.validate_quantity(quantity),
            "confidence": DeviceValidator.validate_confidence(confidence)
        }
        
        # Business logic validations
        # ACB/MCCB typically have 3 or 4 poles
        if validated["category"] in ["ACB", "MCCB"]:
            if validated["poles"] and validated["poles"] not in [3, 4]:
                logger.warning(
                    f"{validated['category']} with unusual pole count: {validated['poles']}"
                )
        
        # MCB typically 1-2 poles
        if validated["category"] == "MCB":
            if validated["poles"] and validated["poles"] > 2:
                logger.warning(
                    f"MCB with unusual pole count: {validated['poles']}"
                )
        
        # High current devices should have higher Icu
        if validated["in_a"] and validated["in_a"] >= 400:
            if validated["icu_ka"] and validated["icu_ka"] < 30:
                logger.warning(
                    f"High current device ({validated['in_a']}A) with low Icu ({validated['icu_ka']}kA)"
                )
        
        return validated
    
    @staticmethod
    def validate_device_list(devices: List[dict]) -> List[dict]:
        """
        Validate list of devices
        Returns validated list, filters out invalid devices
        """
        validated = []
        errors = []
        
        for idx, device in enumerate(devices):
            try:
                validated_device = DeviceValidator.validate_device_spec(
                    category=device.get("category", "OTHER"),
                    in_a=device.get("in_a"),
                    icu_ka=device.get("icu_ka"),
                    poles=device.get("poles"),
                    quantity=device.get("quantity", 1),
                    confidence=device.get("confidence", 0.95)
                )
                # Merge with original data
                validated_device.update(device)
                validated.append(validated_device)
            except DeviceValidationError as e:
                errors.append({
                    "index": idx,
                    "device": device,
                    "error": str(e)
                })
                logger.warning(f"Device {idx} validation failed: {str(e)}")
        
        if errors:
            logger.warning(f"Filtered out {len(errors)} invalid devices from {len(devices)}")
        
        logger.info(f"Validated {len(validated)}/{len(devices)} devices")
        return validated


class ProjectValidator:
    """Validate project-level data"""
    
    @staticmethod
    def validate_project_id(project_id: int) -> int:
        """Validate project ID"""
        if project_id <= 0:
            raise ValueError(f"Project ID phải > 0: {project_id}")
        return project_id
    
    @staticmethod
    def validate_user_tokens(user_tokens: int, required_tokens: int) -> bool:
        """
        Validate user has enough tokens
        Raises TokenLimitExceededError if not enough
        """
        from app.core.exceptions import TokenLimitExceededError
        
        if user_tokens < required_tokens:
            raise TokenLimitExceededError(
                f"Không đủ token: có {user_tokens}, cần {required_tokens}",
                {
                    "available": user_tokens,
                    "required": required_tokens,
                    "deficit": required_tokens - user_tokens
                }
            )
        
        return True


# Convenience functions
def validate_file(file_path: str, filename: Optional[str] = None) -> Tuple[str, int]:
    """Quick file validation"""
    return FileValidator.validate_file(file_path, filename)


def validate_device(device_dict: dict) -> dict:
    """Quick device validation"""
    return DeviceValidator.validate_device_spec(**device_dict)


def validate_devices(devices: List[dict]) -> List[dict]:
    """Quick device list validation"""
    return DeviceValidator.validate_device_list(devices)

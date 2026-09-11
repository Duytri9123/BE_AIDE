"""
Token estimation utilities cho AI API calls
"""
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class TokenEstimator:
    """Estimate tokens for AI API billing"""
    
    @staticmethod
    def estimate_from_text(text: str) -> int:
        """
        Estimate tokens từ text length
        Sử dụng ratio ~4 characters = 1 token (GPT-4 average)
        """
        if not text:
            return 0
        
        char_count = len(text)
        # Use TOKEN_PER_1K_CHARS from settings
        tokens = int((char_count / 1000) * settings.TOKEN_PER_1K_CHARS)
        return max(tokens, 1)  # At least 1 token
    
    @staticmethod
    def estimate_extraction_cost(
        device_count: int,
        response_text: Optional[str] = None,
        include_base_cost: bool = True
    ) -> int:
        """
        Estimate tổng token cost cho một lần extraction
        
        Args:
            device_count: Số lượng thiết bị được extract
            response_text: Text response từ AI (nếu có)
            include_base_cost: Có tính base cost không
        
        Returns:
            Estimated token count
        """
        total = 0
        
        # Base cost (prompt + overhead)
        if include_base_cost:
            total += settings.TOKEN_BASE_COST
        
        # Cost per device extracted
        total += device_count * settings.TOKEN_PER_DEVICE
        
        # If we have actual response text, use it for more accurate estimate
        if response_text:
            response_tokens = TokenEstimator.estimate_from_text(response_text)
            # Use the larger of device-based or text-based estimate
            device_tokens = device_count * settings.TOKEN_PER_DEVICE
            total = settings.TOKEN_BASE_COST + max(device_tokens, response_tokens)
        
        logger.debug(f"Estimated tokens: {total} (base={settings.TOKEN_BASE_COST}, devices={device_count})")
        return total
    
    @staticmethod
    def estimate_from_usage(usage_dict: dict) -> int:
        """
        Extract actual token count từ API response usage
        
        Args:
            usage_dict: Usage object từ API response (OpenAI format)
                Example: {"prompt_tokens": 150, "completion_tokens": 200, "total_tokens": 350}
        
        Returns:
            Total tokens used
        """
        if not usage_dict:
            return 0
        
        # Try different formats
        if "total_tokens" in usage_dict:
            return int(usage_dict["total_tokens"])
        
        if "prompt_tokens" in usage_dict and "completion_tokens" in usage_dict:
            return int(usage_dict["prompt_tokens"]) + int(usage_dict["completion_tokens"])
        
        # Gemini format
        if "promptTokenCount" in usage_dict and "candidatesTokenCount" in usage_dict:
            return int(usage_dict["promptTokenCount"]) + int(usage_dict["candidatesTokenCount"])
        
        return 0
    
    @staticmethod
    def can_afford(user_tokens: int, estimated_cost: int) -> tuple[bool, int]:
        """
        Check if user has enough tokens
        
        Returns:
            (can_afford: bool, remaining_tokens: int)
        """
        remaining = user_tokens - estimated_cost
        return remaining >= 0, remaining


# Convenience functions
def estimate_tokens(text: str) -> int:
    """Quick token estimation from text"""
    return TokenEstimator.estimate_from_text(text)


def estimate_extraction_tokens(device_count: int, response_text: Optional[str] = None) -> int:
    """Quick estimation for extraction cost"""
    return TokenEstimator.estimate_extraction_cost(device_count, response_text)

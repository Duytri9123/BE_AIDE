"""
Token estimation utilities cho AI API calls
"""
import contextlib
import contextvars
import logging
import math
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

TOKENS_PER_CREDIT = 1000
_ai_usage_tracker: contextvars.ContextVar[Optional[dict]] = contextvars.ContextVar("ai_usage_tracker", default=None)


def tokens_to_credits(tokens: Optional[int]) -> int:
    """Convert raw token balance to integer credits (1 credit = 1,000 tokens)."""
    if tokens is None or isinstance(tokens, bool):
        return 0
    return max(0, int(tokens) // TOKENS_PER_CREDIT)


def usage_credits(tokens: Optional[int]) -> int:
    """Convert consumed tokens into billed credits (rounded up, min 1 when > 0)."""
    if tokens is None or isinstance(tokens, bool) or int(tokens) <= 0:
        return 0
    return math.ceil(int(tokens) / TOKENS_PER_CREDIT)


def record_ai_usage(prompt_tokens=0, output_tokens=0, thinking_tokens=0) -> None:
    """Accumulate AI token usage into the active tracked_ai_usage scope."""
    tracker = _ai_usage_tracker.get()
    if tracker is None:
        return
    pt = int(prompt_tokens or 0) if str(prompt_tokens or "").isdigit() or isinstance(prompt_tokens, (int, float)) else 0
    ot = int(output_tokens or 0) if str(output_tokens or "").isdigit() or isinstance(output_tokens, (int, float)) else 0
    tt = int(thinking_tokens or 0) if str(thinking_tokens or "").isdigit() or isinstance(thinking_tokens, (int, float)) else 0
    tracker["prompt_tokens"] += max(0, pt)
    tracker["output_tokens"] += max(0, ot)
    tracker["thinking_tokens"] += max(0, tt)
    tracker["total_tokens"] += max(0, pt) + max(0, ot) + max(0, tt)
    tracker["calls"] += 1


@contextlib.contextmanager
def tracked_ai_usage():
    """Collect total AI usage across nested async/task calls without changing return types."""
    bucket = {"prompt_tokens": 0, "output_tokens": 0, "thinking_tokens": 0, "total_tokens": 0, "calls": 0}
    token = _ai_usage_tracker.set(bucket)
    try:
        yield bucket
    finally:
        _ai_usage_tracker.reset(token)


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

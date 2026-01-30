from enum import Enum


class ErrorCode(str, Enum):
    # Client Errors (4xx)
    INVALID_REQUEST = "INVALID_REQUEST"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # Server Errors (5xx)
    GPU_UNAVAILABLE = "GPU_UNAVAILABLE"
    API_ERROR = "API_ERROR"
    QUEUE_ERROR = "QUEUE_ERROR"
    CACHE_ERROR = "CACHE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    
    # Retry Errors
    MAX_RETRIES_EXCEEDED = "MAX_RETRIES_EXCEEDED"
    TIMEOUT = "TIMEOUT"


class ErrorContract:
    """Standardized error contracts."""
    
    @staticmethod
    def invalid_request(details: str) -> dict:
        return {
            "error_code": ErrorCode.INVALID_REQUEST,
            "message": "Invalid request parameters",
            "details": {"reason": details}
        }
    
    @staticmethod
    def gpu_unavailable() -> dict:
        return {
            "error_code": ErrorCode.GPU_UNAVAILABLE,
            "message": "GPU mode not available on this system",
            "details": {"suggestion": "Use /api or /auto endpoint"}
        }
    
    @staticmethod
    def api_error(error: str) -> dict:
        return {
            "error_code": ErrorCode.API_ERROR,
            "message": "External API error",
            "details": {"error": error}
        }
    
    @staticmethod
    def idempotency_conflict(existing_result: str) -> dict:
        return {
            "error_code": ErrorCode.IDEMPOTENCY_CONFLICT,
            "message": "Request with this idempotency key already processed",
            "details": {"existing_result": existing_result}
        }

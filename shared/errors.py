"""统一错误层级 + 重试策略。"""

from __future__ import annotations


class StepError(Exception):
    """步骤执行错误基类。所有步骤错误继承此类。"""

    error_type: str = "unknown"

    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)


class InputMissingError(StepError):
    error_type = "input_missing"


class InputInvalidError(StepError):
    error_type = "input_invalid"


class ProcessingError(StepError):
    error_type = "processing"


class AIProviderError(StepError):
    error_type = "ai"


class AIRateLimitError(AIProviderError):
    error_type = "ai_rate_limit"


class AITimeoutError(StepError):
    error_type = "timeout"


class ResourceError(StepError):
    error_type = "resource"


class AllProvidersFailedError(AIProviderError):
    """所有 AI Provider 都失败（primary + fallback + text_fallback）。"""

    error_type = "ai"


RETRY_POLICY: dict[str, dict] = {
    "input_missing": {"max": 0},
    "input_invalid": {"max": 0},
    "processing": {"max": 1, "delay": [0]},
    "ai": {"max": 3, "delay": [30, 60, 120]},
    "ai_rate_limit": {"max": 3, "delay": [30, 30, 30]},
    "timeout": {"max": 1, "delay": [10]},
    "resource": {"max": 0},
}


def get_retry_delay(error_type: str, attempt: int) -> int | None:
    """返回第 attempt 次重试的延迟秒数，None 表示不应重试。"""
    policy = RETRY_POLICY.get(error_type)
    if policy is None or attempt >= policy["max"]:
        return None
    delays = policy.get("delay", [])
    if not delays:
        return 0
    return delays[min(attempt, len(delays) - 1)]

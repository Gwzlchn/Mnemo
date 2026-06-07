"""统一错误层级 + 重试策略。"""

from __future__ import annotations


class StepError(Exception):
    """步骤执行错误基类。所有步骤错误继承此类。error_type 决定重试策略。"""

    error_type: str = "unknown"

    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)


class InputMissingError(StepError):
    """BUILD：上游产物缺失，重试也不会出现，不重试。"""

    error_type = "input_missing"


class InputInvalidError(StepError):
    """BUILD：输入存在但内容/格式非法，确定性失败，不重试。"""

    error_type = "input_invalid"


class ProcessingError(StepError):
    """SYSTEM-ish：步骤处理中途异常，可能是瞬态，重试一次。"""

    error_type = "processing"


class AIProviderError(StepError):
    """SYSTEM：AI Provider 调用失败（网络/服务端 5xx），退避重试。"""

    error_type = "ai"


class AIRateLimitError(AIProviderError):
    """SYSTEM：触发限流，固定间隔重试等待配额恢复。"""

    error_type = "ai_rate_limit"


class AITimeoutError(StepError):
    """SYSTEM：调用超时，瞬态，短延迟重试一次。"""

    error_type = "timeout"


class ResourceError(StepError):
    """SYSTEM-pressure：OOM/磁盘满，立即重试难自愈，故归类不重试。"""

    error_type = "resource"


class AllProvidersFailedError(AIProviderError):
    """所有 AI Provider 都失败（primary + fallback + text_fallback）。"""

    error_type = "ai"


# 重试策略：按 error_type 区分 BUILD（步骤自身确定性失败，重试无意义）
# 与 SYSTEM/transient（基础设施瞬态故障，退避重试可能恢复）。
#
# 分类映射（与各 StepError 子类的 docstring 对应）：
#   BUILD（max 0，不重试）：
#     input_missing  上游产物缺失
#     input_invalid  输入内容/格式非法
#     resource       OOM/磁盘满——属资源压力，但立即重试极少自愈，故同样不重试
#     unknown        未知/未分类失败——保守不重试（见下方说明）
#   SYSTEM / transient（退避重试）：
#     processing     处理中途异常，可能瞬态                 max 1
#     ai             Provider 网络/5xx，指数退避            max 3 [30,60,120]
#     ai_rate_limit  限流，固定间隔等配额恢复               max 3 [30,30,30]
#     timeout        调用超时，瞬态                         max 1 [10]
#
# 关于 unknown：步骤内未捕获异常由 step_base 写入 error_type="unknown"（区别于
# worker 编排层异常映射的 "processing"）。unknown 不在表中——get_retry_delay 与
# 调度器对缺表项均按 max 0 处理，即不重试。这是有意的 BUILD 兜底：未能归类的
# 失败默认当作步骤自身缺陷，避免对未知错误盲目重试放大故障。
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

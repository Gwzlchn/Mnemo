"""tests for shared/errors.py"""

from shared.errors import (
    RETRY_POLICY,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
    AllProvidersFailedError,
    InputInvalidError,
    InputMissingError,
    ProcessingError,
    ResourceError,
    StepError,
    get_retry_delay,
)


class TestErrorTypes:
    def test_base_error_type(self):
        assert StepError.error_type == "unknown"

    def test_input_missing(self):
        e = InputMissingError("file.json")
        assert e.error_type == "input_missing"
        assert "file.json" in str(e)

    def test_input_invalid(self):
        assert InputInvalidError.error_type == "input_invalid"

    def test_processing(self):
        assert ProcessingError.error_type == "processing"

    def test_ai_provider(self):
        assert AIProviderError.error_type == "ai"

    def test_ai_rate_limit(self):
        assert AIRateLimitError.error_type == "ai_rate_limit"

    def test_ai_timeout(self):
        assert AITimeoutError.error_type == "timeout"

    def test_resource(self):
        assert ResourceError.error_type == "resource"

    def test_all_providers_failed(self):
        assert AllProvidersFailedError.error_type == "ai"


class TestInheritance:
    def test_all_inherit_step_error(self):
        for cls in [
            InputMissingError,
            InputInvalidError,
            ProcessingError,
            AIProviderError,
            AIRateLimitError,
            AITimeoutError,
            ResourceError,
            AllProvidersFailedError,
        ]:
            assert issubclass(cls, StepError)

    def test_rate_limit_is_ai_provider(self):
        assert issubclass(AIRateLimitError, AIProviderError)

    def test_all_providers_is_ai_provider(self):
        assert issubclass(AllProvidersFailedError, AIProviderError)

    def test_isinstance_check(self):
        e = AIRateLimitError("rate limited")
        assert isinstance(e, AIProviderError)
        assert isinstance(e, StepError)


class TestRetryPolicy:
    def test_covers_all_error_types(self):
        all_types = {
            cls.error_type
            for cls in [
                InputMissingError,
                InputInvalidError,
                ProcessingError,
                AIProviderError,
                AIRateLimitError,
                AITimeoutError,
                ResourceError,
            ]
        }
        assert all_types == set(RETRY_POLICY.keys())

    def test_delay_length_ge_max(self):
        for error_type, policy in RETRY_POLICY.items():
            if policy["max"] > 0:
                assert len(policy["delay"]) >= policy["max"], (
                    f"{error_type}: delay length < max"
                )

    def test_no_retry_errors(self):
        assert RETRY_POLICY["input_missing"]["max"] == 0
        assert RETRY_POLICY["input_invalid"]["max"] == 0
        assert RETRY_POLICY["resource"]["max"] == 0


class TestGetRetryDelay:
    def test_no_retry(self):
        assert get_retry_delay("input_missing", 0) is None
        assert get_retry_delay("resource", 0) is None

    def test_first_attempt(self):
        assert get_retry_delay("processing", 0) == 0
        assert get_retry_delay("ai", 0) == 30
        assert get_retry_delay("timeout", 0) == 10

    def test_exponential_backoff(self):
        assert get_retry_delay("ai", 0) == 30
        assert get_retry_delay("ai", 1) == 60
        assert get_retry_delay("ai", 2) == 120

    def test_exceeds_max(self):
        assert get_retry_delay("ai", 3) is None
        assert get_retry_delay("processing", 1) is None

    def test_unknown_error_type(self):
        assert get_retry_delay("nonexistent", 0) is None

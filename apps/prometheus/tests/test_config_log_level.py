"""Tests for Settings.log_level field_validator (Phase 22-02)."""

import pytest
from pydantic import ValidationError

from localstock.config import Settings


def test_log_level_default_is_info(monkeypatch):
    # Bypass .env loading and shell env so we observe the field default.
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    s = Settings(_env_file=None)
    assert s.log_level == "INFO"


def test_log_level_lowercase_normalized_to_uppercase():
    assert Settings(log_level="debug").log_level == "DEBUG"
    assert Settings(log_level="trace").log_level == "TRACE"
    assert Settings(log_level="success").log_level == "SUCCESS"


def test_log_level_mixed_case_normalized():
    assert Settings(log_level="Warning").log_level == "WARNING"


@pytest.mark.parametrize(
    "level",
    ["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"],
)
def test_log_level_accepts_all_loguru_levels(level):
    assert Settings(log_level=level).log_level == level


def test_log_level_invalid_raises_validation_error():
    with pytest.raises(ValidationError) as exc_info:
        Settings(log_level="verbose")
    assert "log_level must be one of" in str(exc_info.value)


def test_log_level_non_string_raises_validation_error():
    with pytest.raises(ValidationError) as exc_info:
        Settings(log_level=123)
    assert "log_level must be a string" in str(exc_info.value)

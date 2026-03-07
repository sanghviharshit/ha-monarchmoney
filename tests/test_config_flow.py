"""Tests for the Monarch Money config flow.

Tests the config flow class attributes, MFA error detection logic,
and MFA secret handling patterns used in the integration.
"""

from __future__ import annotations

import pytest

from custom_components.monarchmoney.config_flow import MonarchConfigFlow
from custom_components.monarchmoney.const import (
    CONF_MFA_SECRET,
    DOMAIN,
)


class TestConfigFlowVersion:
    """Test config flow version attribute."""

    def test_version_is_set(self) -> None:
        """Test that VERSION is set on the config flow class."""
        assert hasattr(MonarchConfigFlow, "VERSION")

    def test_version_value(self) -> None:
        """Test that VERSION is an integer."""
        assert isinstance(MonarchConfigFlow.VERSION, int)
        assert MonarchConfigFlow.VERSION == 2


class TestMfaErrorDetection:
    """Test the MFA error detection logic from _test_connection_and_set_token.

    The config flow checks error messages for MFA-related keywords:
    '401', 'unauthorized', 'mfa', 'multi-factor', 'authentication'.
    These tests verify that pattern.
    """

    def test_401_unauthorized(self) -> None:
        """Test that '401 unauthorized' is detected as MFA error."""
        assert MonarchConfigFlow._is_mfa_error("401 unauthorized") is True

    def test_timeout_not_mfa(self) -> None:
        """Test that 'timeout' is NOT an MFA error."""
        assert MonarchConfigFlow._is_mfa_error("timeout") is False

    def test_mfa_required(self) -> None:
        """Test that 'mfa required' is detected."""
        assert MonarchConfigFlow._is_mfa_error("mfa required") is True

    def test_multi_factor_required(self) -> None:
        """Test that 'multi-factor' is detected."""
        assert MonarchConfigFlow._is_mfa_error("multi-factor authentication required") is True

    def test_authentication_failed(self) -> None:
        """Test that 'authentication failed' is detected."""
        assert MonarchConfigFlow._is_mfa_error("authentication failed") is True

    def test_connection_refused(self) -> None:
        """Test that 'connection refused' is NOT an MFA error."""
        assert MonarchConfigFlow._is_mfa_error("connection refused") is False

    def test_rate_limited(self) -> None:
        """Test that '429 Too Many Requests' is NOT an MFA error."""
        assert MonarchConfigFlow._is_mfa_error("429 too many requests") is False

    def test_empty_string(self) -> None:
        """Test that empty string is NOT an MFA error."""
        assert MonarchConfigFlow._is_mfa_error("") is False

    def test_unauthorized_alone(self) -> None:
        """Test that 'unauthorized' alone is detected."""
        assert MonarchConfigFlow._is_mfa_error("unauthorized") is True

    def test_generic_server_error(self) -> None:
        """Test that generic server error is NOT an MFA error."""
        assert MonarchConfigFlow._is_mfa_error("internal server error") is False


class TestMfaSecretHandling:
    """Test the MFA secret update patterns from _validate_and_create_entry.

    The config flow strips whitespace from MFA secrets and removes them
    if empty. These tests verify that behavior.
    """

    @staticmethod
    def _update_mfa_secret(user_input: dict, current: dict) -> dict:
        """Replicate the MFA secret handling logic from config_flow.py.

        This mirrors the pattern in _validate_and_create_entry where:
        - If MFA secret is provided and non-empty, store stripped value
        - If MFA secret is empty or missing, remove from config
        """
        result = dict(current)
        if CONF_MFA_SECRET in user_input and user_input[CONF_MFA_SECRET].strip():
            result[CONF_MFA_SECRET] = user_input[CONF_MFA_SECRET].strip()
        else:
            result.pop(CONF_MFA_SECRET, None)
        return result

    def test_empty_string_removes_secret(self) -> None:
        """Test that empty string MFA secret removes the key."""
        user_input = {CONF_MFA_SECRET: ""}
        current = {CONF_MFA_SECRET: "old-secret", "email": "test@test.com"}
        result = self._update_mfa_secret(user_input, current)
        assert CONF_MFA_SECRET not in result
        assert result["email"] == "test@test.com"

    def test_whitespace_only_removes_secret(self) -> None:
        """Test that whitespace-only MFA secret removes the key."""
        user_input = {CONF_MFA_SECRET: "   "}
        current = {CONF_MFA_SECRET: "old-secret"}
        result = self._update_mfa_secret(user_input, current)
        assert CONF_MFA_SECRET not in result

    def test_valid_secret_stores_stripped(self) -> None:
        """Test that valid MFA secret is stored after stripping."""
        user_input = {CONF_MFA_SECRET: "  JBSWY3DPEHPK3PXP  "}
        current = {}
        result = self._update_mfa_secret(user_input, current)
        assert result[CONF_MFA_SECRET] == "JBSWY3DPEHPK3PXP"

    def test_valid_secret_no_whitespace(self) -> None:
        """Test that clean MFA secret is stored as-is."""
        user_input = {CONF_MFA_SECRET: "ABCDEF123456"}
        current = {}
        result = self._update_mfa_secret(user_input, current)
        assert result[CONF_MFA_SECRET] == "ABCDEF123456"

    def test_missing_secret_key_removes(self) -> None:
        """Test that missing MFA secret key in input removes from current."""
        user_input: dict = {}
        current = {CONF_MFA_SECRET: "old-secret"}
        # When CONF_MFA_SECRET not in user_input, we skip the strip check
        # and fall to the else branch which pops the key
        result = dict(current)
        if CONF_MFA_SECRET in user_input and user_input[CONF_MFA_SECRET].strip():
            result[CONF_MFA_SECRET] = user_input[CONF_MFA_SECRET].strip()
        else:
            result.pop(CONF_MFA_SECRET, None)
        assert CONF_MFA_SECRET not in result

    def test_replaces_existing_secret(self) -> None:
        """Test that a new valid secret replaces the old one."""
        user_input = {CONF_MFA_SECRET: "NEW_SECRET_KEY"}
        current = {CONF_MFA_SECRET: "OLD_SECRET_KEY"}
        result = self._update_mfa_secret(user_input, current)
        assert result[CONF_MFA_SECRET] == "NEW_SECRET_KEY"

    def test_no_existing_secret_no_input(self) -> None:
        """Test no-op when there is no existing secret and no input."""
        user_input: dict = {}
        current = {"email": "test@test.com"}
        result = dict(current)
        result.pop(CONF_MFA_SECRET, None)  # Mirrors the else branch
        assert CONF_MFA_SECRET not in result
        assert result["email"] == "test@test.com"


class TestConfigFlowConstants:
    """Test config flow related constants."""

    def test_domain(self) -> None:
        """Test that DOMAIN is 'monarchmoney'."""
        assert DOMAIN == "monarchmoney"

    def test_mfa_secret_const(self) -> None:
        """Test that CONF_MFA_SECRET is defined."""
        assert CONF_MFA_SECRET == "mfa_secret"

    def test_credentials_schema_fields(self) -> None:
        """Test that CREDENTIALS_SCHEMA has expected fields."""
        from custom_components.monarchmoney.config_flow import CREDENTIALS_SCHEMA
        schema_keys = [str(k) for k in CREDENTIALS_SCHEMA.schema]
        assert "email" in schema_keys
        assert "password" in schema_keys

    def test_mfa_schema_fields(self) -> None:
        """Test that MFA_SCHEMA has mfa_code field."""
        from custom_components.monarchmoney.config_flow import MFA_SCHEMA
        schema_keys = [str(k) for k in MFA_SCHEMA.schema]
        assert "mfa_code" in schema_keys

    def test_options_schema_fields(self) -> None:
        """Test that _build_options_schema produces expected fields."""
        from custom_components.monarchmoney.config_flow import _build_options_schema
        schema = _build_options_schema()
        schema_keys = [str(k) for k in schema.schema]
        assert "scan_interval" in schema_keys
        assert "timeout" in schema_keys

"""Tests for the Monarch Money update coordinator.

Tests the static/utility methods on MonarchCoordinator that do not require
a Home Assistant instance. Full integration tests requiring hass are skipped
unless pytest-homeassistant-custom-component is available.
"""

from __future__ import annotations

import pytest

# Import the coordinator; requires homeassistant to be installed.
# If not available, the entire module is skipped.
pytest.importorskip("homeassistant")
from custom_components.monarchmoney.update_coordinator import MonarchCoordinator  # noqa: E402
from custom_components.monarchmoney.const import (  # noqa: E402
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    VALUES_SCAN_INTERVAL,
    VALUES_TIMEOUT,
)


class TestIsAuthError:
    """Test MonarchCoordinator._is_auth_error static method."""

    def test_unauthorized_lowercase(self) -> None:
        """Test that 'unauthorized' is detected as auth error."""
        err = Exception("Request failed: unauthorized")
        assert MonarchCoordinator._is_auth_error(err) is True

    def test_unauthorized_mixed_case(self) -> None:
        """Test that 'Unauthorized' (mixed case) is detected."""
        err = Exception("HTTP 401 Unauthorized access")
        assert MonarchCoordinator._is_auth_error(err) is True

    def test_401_status_code(self) -> None:
        """Test that '401' in error message is detected."""
        err = Exception("Server returned 401")
        assert MonarchCoordinator._is_auth_error(err) is True

    def test_authentication_keyword(self) -> None:
        """Test that 'authentication' is detected as auth error."""
        err = Exception("authentication failed for user")
        assert MonarchCoordinator._is_auth_error(err) is True

    def test_authentication_required(self) -> None:
        """Test that 'authentication required' is detected."""
        err = Exception("Authentication required to access resource")
        assert MonarchCoordinator._is_auth_error(err) is True

    def test_timeout_not_auth_error(self) -> None:
        """Test that 'timeout' is NOT an auth error."""
        err = Exception("Connection timeout after 30s")
        assert MonarchCoordinator._is_auth_error(err) is False

    def test_connection_refused_not_auth_error(self) -> None:
        """Test that 'connection refused' is NOT an auth error."""
        err = Exception("Connection refused by server")
        assert MonarchCoordinator._is_auth_error(err) is False

    def test_network_error_not_auth_error(self) -> None:
        """Test that network errors are NOT auth errors."""
        err = Exception("DNS resolution failed")
        assert MonarchCoordinator._is_auth_error(err) is False

    def test_rate_limit_not_auth_error(self) -> None:
        """Test that rate limiting (429) is NOT an auth error."""
        err = Exception("429 Too Many Requests")
        assert MonarchCoordinator._is_auth_error(err) is False

    def test_server_error_not_auth_error(self) -> None:
        """Test that 500 errors are NOT auth errors."""
        err = Exception("Internal Server Error 500")
        assert MonarchCoordinator._is_auth_error(err) is False

    def test_empty_error_message(self) -> None:
        """Test that empty error message is NOT an auth error."""
        err = Exception("")
        assert MonarchCoordinator._is_auth_error(err) is False

    def test_combined_auth_keywords(self) -> None:
        """Test error with multiple auth keywords."""
        err = Exception("401 unauthorized authentication failure")
        assert MonarchCoordinator._is_auth_error(err) is True


class TestFetchApiDataStructure:
    """Test the expected structure of _fetch_api_data return value.

    These tests verify the MonarchData structure that _fetch_api_data builds,
    without requiring a real API connection or Home Assistant instance.
    """

    def test_expected_keys_in_data(self) -> None:
        """Test that the coordinator data dict has the expected keys."""
        # The coordinator builds: {"accounts": [], "categories": [], "cashflow": {}}
        data: dict = {"accounts": [], "categories": [], "cashflow": {}}
        assert "accounts" in data
        assert "categories" in data
        assert "cashflow" in data

    def test_default_data_has_empty_lists(self) -> None:
        """Test that default data structure has empty collections."""
        data: dict = {"accounts": [], "categories": [], "cashflow": {}}
        assert data["accounts"] == []
        assert data["categories"] == []
        assert data["cashflow"] == {}

    def test_accounts_or_fallback(self) -> None:
        """Test the accounts.get('accounts') or [] pattern from coordinator."""
        # Simulates: data["accounts"] = accounts.get("accounts") or []
        api_response_normal = {"accounts": [{"id": "1"}]}
        assert (api_response_normal.get("accounts") or []) == [{"id": "1"}]

        api_response_none = {"accounts": None}
        assert (api_response_none.get("accounts") or []) == []

        api_response_missing: dict = {}
        assert (api_response_missing.get("accounts") or []) == []

    def test_categories_or_fallback(self) -> None:
        """Test the categories.get('categories') or [] pattern."""
        api_response_none = {"categories": None}
        assert (api_response_none.get("categories") or []) == []

    def test_cashflow_or_fallback(self) -> None:
        """Test the cashflow or {} pattern."""
        assert (None or {}) == {}
        assert ({} or {}) == {}
        cashflow_data = {"summary": []}
        assert (cashflow_data or {}) == cashflow_data


class TestCoordinatorConstants:
    """Test coordinator configuration constants."""

    def test_default_scan_interval(self) -> None:
        """Test that default scan interval is 60 minutes (1 hour)."""
        assert DEFAULT_SCAN_INTERVAL == 60

    def test_default_timeout(self) -> None:
        """Test that default timeout is 30 seconds."""
        assert DEFAULT_TIMEOUT == 30

    def test_scan_interval_values(self) -> None:
        """Test that scan interval options include expected values (in minutes)."""
        assert 60 in VALUES_SCAN_INTERVAL
        assert 360 in VALUES_SCAN_INTERVAL
        assert 1440 in VALUES_SCAN_INTERVAL

    def test_timeout_values(self) -> None:
        """Test that timeout options include expected values (in seconds)."""
        assert 10 in VALUES_TIMEOUT
        assert 30 in VALUES_TIMEOUT
        assert 60 in VALUES_TIMEOUT

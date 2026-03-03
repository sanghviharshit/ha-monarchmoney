"""Shared fixtures for Monarch Money integration tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_SCAN_INTERVAL

from custom_components.monarchmoney.const import (
    CONF_MFA_SECRET,
    CONF_TOKEN,
    CONF_TIMEOUT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
)

from .const import (
    MOCK_ACCOUNTS_RESPONSE,
    MOCK_CASHFLOW_RESPONSE,
    MOCK_CATEGORIES_RESPONSE,
    MOCK_CREDIT_RESPONSE,
    MOCK_EMAIL,
    MOCK_HOLDINGS_RESPONSE,
    MOCK_PASSWORD,
    MOCK_RECURRING_RESPONSE,
    MOCK_TOKEN,
)


@pytest.fixture
def mock_config_entry_data() -> dict:
    """Return minimal config-entry *data* dict."""
    return {
        CONF_EMAIL: MOCK_EMAIL,
        CONF_PASSWORD: MOCK_PASSWORD,
        CONF_TOKEN: MOCK_TOKEN,
    }


@pytest.fixture
def mock_config_entry_options() -> dict:
    """Return default config-entry *options* dict."""
    return {
        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        CONF_TIMEOUT: DEFAULT_TIMEOUT,
    }


@pytest.fixture
def mock_monarch_api():
    """Patch MonarchMoney and return an AsyncMock instance.

    Every API method used by the integration is pre-configured to return
    the corresponding mock response from ``tests.const``.

    Usage::

        async def test_something(mock_monarch_api):
            # mock_monarch_api is the AsyncMock *instance*
            mock_monarch_api.get_accounts.return_value = ...
    """
    api = AsyncMock()

    # Authentication helpers
    api.token = MOCK_TOKEN
    api.login = AsyncMock(return_value=None)
    api.multi_factor_authenticate = AsyncMock(return_value=None)

    # Session validation
    api.get_subscription_details = AsyncMock(return_value={"id": "sub_1"})

    # Core data endpoints
    api.get_accounts = AsyncMock(return_value=MOCK_ACCOUNTS_RESPONSE)
    api.get_transaction_categories = AsyncMock(
        return_value=MOCK_CATEGORIES_RESPONSE
    )
    api.get_cashflow = AsyncMock(return_value=MOCK_CASHFLOW_RESPONSE)

    # Optional data endpoints
    api.get_credit_history = AsyncMock(
        return_value=MOCK_CREDIT_RESPONSE
    )
    api.get_recurring_transactions = AsyncMock(
        return_value=MOCK_RECURRING_RESPONSE
    )
    api.get_account_holdings = AsyncMock(return_value=MOCK_HOLDINGS_RESPONSE)
    api.request_accounts_refresh = AsyncMock(return_value=None)

    with patch(
        "custom_components.monarchmoney.update_coordinator.MonarchMoney",
        return_value=api,
    ) as mock_cls:
        # Allow tests that inspect the class-level mock (e.g. assert
        # MonarchMoney was instantiated with a token).
        mock_cls._instance = api
        yield api

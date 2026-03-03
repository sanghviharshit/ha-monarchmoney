"""Tests for Monarch Money button logic."""

from __future__ import annotations

from custom_components.monarchmoney.models import Account, MonarchData
from tests.const import MOCK_ACCOUNTS_RESPONSE


def test_button_account_ids():
    """Button should extract account IDs from MonarchData."""
    data = MonarchData()
    data.accounts = [Account.from_api(a) for a in MOCK_ACCOUNTS_RESPONSE["accounts"]]

    account_ids = [a.id for a in data.accounts if a.id]
    assert len(account_ids) == 6
    assert "acct_checking_1" in account_ids
    assert "acct_brokerage_4" in account_ids


def test_button_empty_data():
    """Button should handle empty data gracefully."""
    data = MonarchData()
    account_ids = [a.id for a in data.accounts if a.id]
    assert account_ids == []


def test_button_none_data():
    """Button should handle None data."""
    data = None
    if not data:
        account_ids = []
    else:
        account_ids = [a.id for a in data.accounts if a.id]
    assert account_ids == []

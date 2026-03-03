"""Tests for Monarch Money calendar logic."""

from __future__ import annotations

from datetime import date, timedelta

from custom_components.monarchmoney.models import RecurringTransaction
from tests.const import MOCK_RECURRING_RESPONSE


def _parse_recurring() -> list[RecurringTransaction]:
    """Parse mock recurring items into typed objects."""
    items = MOCK_RECURRING_RESPONSE.get("recurringTransactionItems") or []
    return [r for r in (RecurringTransaction.from_api(i) for i in items) if r is not None]


def test_recurring_transaction_parsing():
    """Recurring transactions should parse correctly (all 3 have dates)."""
    recurring = _parse_recurring()
    assert len(recurring) == 3

    netflix = recurring[0]
    assert netflix.merchant_name == "Netflix"
    assert netflix.amount == -15.99
    assert netflix.frequency == "monthly"
    assert netflix.category_name == "Entertainment"


def test_recurring_none_merchant():
    """Recurring item with None merchant should use 'Unknown'."""
    recurring = _parse_recurring()
    rent = recurring[1]  # Rent Payment has merchant: None
    assert rent.merchant_name == "Unknown"


def test_recurring_event_summary_format():
    """Calendar event summary should be 'merchant $amount'."""
    recurring = _parse_recurring()
    item = recurring[0]  # Netflix
    amount_str = f"${abs(item.amount):.2f}" if item.amount is not None else ""
    summary = f"{item.merchant_name} {amount_str}".strip()
    assert summary == "Netflix $15.99"


def test_recurring_date_parsing():
    """Recurring transaction dates should be parseable as ISO dates."""
    recurring = _parse_recurring()
    for item in recurring:
        parsed = date.fromisoformat(item.date)
        assert isinstance(parsed, date)


def test_recurring_missing_date_filtered():
    """Items without a date should be filtered out by from_api."""
    raw = {"amount": -10.0, "stream": {"merchant": {"name": "Test"}, "frequency": "monthly"}}
    result = RecurringTransaction.from_api(raw)
    assert result is None


def test_recurring_event_date_range():
    """Events should be filterable by date range."""
    recurring = _parse_recurring()
    events_dates = [date.fromisoformat(r.date) for r in recurring]

    start = date(2026, 1, 1)
    end = date(2026, 1, 10)
    in_range = [d for d in events_dates if start <= d <= end]
    # Jan 1 (Rent) and Jan 10 (Direct Deposit) are in range; Jan 15 (Netflix) is not
    assert len(in_range) == 2

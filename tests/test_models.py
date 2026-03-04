"""Tests for Monarch Money typed dataclass models (models.py)."""

from __future__ import annotations

from custom_components.monarchmoney.models import (
    Account,
    AccountHoldings,
    AccountType,
    CashflowData,
    CreditHistory,
    Holding,
    HouseholdUser,
    Institution,
    MonarchData,
    RecurringTransaction,
    TransactionCategory,
)
from tests.const import (
    MOCK_ACCOUNTS_RESPONSE,
    MOCK_CASHFLOW_RESPONSE,
    MOCK_CATEGORIES_RESPONSE,
    MOCK_CREDIT_RESPONSE,
    MOCK_HOLDINGS_RESPONSE,
    MOCK_RECURRING_RESPONSE,
)


# ---------------------------------------------------------------------------
# Account models
# ---------------------------------------------------------------------------


class TestAccountFromApi:
    def test_valid_account(self) -> None:
        raw = MOCK_ACCOUNTS_RESPONSE["accounts"][0]
        a = Account.from_api(raw)
        assert a.id == "acct_checking_1"
        assert a.display_name == "Primary Checking"
        assert a.display_balance == 5432.10
        assert a.account_type.name == "depository"
        assert a.institution.name == "Test Bank"
        assert a.include_in_net_worth is True
        assert a.is_hidden is False
        assert a.is_asset is True

    def test_missing_fields(self) -> None:
        a = Account.from_api({})
        assert a.id == ""
        assert a.display_name == ""
        assert a.account_type.name == ""
        assert a.institution.name == ""

    def test_none_credential(self) -> None:
        raw = {"id": "x", "credential": None}
        a = Account.from_api(raw)
        assert a.institution.name == ""


class TestAccountType:
    def test_from_api(self) -> None:
        assert AccountType.from_api({"name": "brokerage"}).name == "brokerage"

    def test_empty(self) -> None:
        assert AccountType.from_api({}).name == ""


class TestInstitution:
    def test_from_api(self) -> None:
        assert Institution.from_api({"name": "Chase"}).name == "Chase"


# ---------------------------------------------------------------------------
# Category models
# ---------------------------------------------------------------------------


class TestTransactionCategory:
    def test_income_category(self) -> None:
        raw = MOCK_CATEGORIES_RESPONSE["categories"][0]
        cat = TransactionCategory.from_api(raw)
        assert cat.name == "Salary"
        assert cat.group is not None
        assert cat.group.type == "income"

    def test_missing_group(self) -> None:
        cat = TransactionCategory.from_api({"name": "Misc"})
        assert cat.group is None

    def test_none_group(self) -> None:
        cat = TransactionCategory.from_api({"name": "Misc", "group": None})
        assert cat.group is None


# ---------------------------------------------------------------------------
# Cashflow models
# ---------------------------------------------------------------------------


class TestCashflowData:
    def test_valid_cashflow(self) -> None:
        cf = CashflowData.from_api(MOCK_CASHFLOW_RESPONSE)
        assert cf.summary is not None
        assert cf.summary.savings == 1200.50
        assert cf.summary.sum_income == 6500.00
        assert cf.summary.sum_expense == -5299.50
        assert cf.summary.savings_rate == 0.1847

    def test_by_category(self) -> None:
        cf = CashflowData.from_api(MOCK_CASHFLOW_RESPONSE)
        assert len(cf.by_category) > 0
        income_cats = [c for c in cf.by_category if c.category_group_type == "income"]
        assert len(income_cats) == 2

    def test_empty_response(self) -> None:
        cf = CashflowData.from_api({})
        assert cf.summary is None
        assert cf.by_category == []

    def test_none_summary(self) -> None:
        cf = CashflowData.from_api({"summary": None})
        assert cf.summary is None


# ---------------------------------------------------------------------------
# Credit models
# ---------------------------------------------------------------------------


class TestCreditHistory:
    def test_valid_credit_history(self) -> None:
        ch = CreditHistory.from_api(MOCK_CREDIT_RESPONSE)
        assert len(ch.snapshots) == 5
        assert len(ch.household_users) == 2

    def test_user_names(self) -> None:
        ch = CreditHistory.from_api(MOCK_CREDIT_RESPONSE)
        names = {u.display_name for u in ch.household_users}
        assert "Alice Test" in names
        assert "Bob Test" in names

    def test_empty_response(self) -> None:
        ch = CreditHistory.from_api({})
        assert ch.snapshots == []
        assert ch.household_users == []


class TestHouseholdUser:
    def test_display_name_preferred(self) -> None:
        u = HouseholdUser.from_api({"id": "1", "displayName": "Alice", "name": "Alice Jones"})
        assert u.display_name == "Alice"

    def test_name_fallback(self) -> None:
        u = HouseholdUser.from_api({"id": "1", "name": "Bob Jones"})
        assert u.display_name == "Bob Jones"

    def test_unknown_fallback(self) -> None:
        u = HouseholdUser.from_api({"id": "1"})
        assert u.display_name == "Unknown"


# ---------------------------------------------------------------------------
# Holdings models
# ---------------------------------------------------------------------------


class TestHolding:
    def test_valid_holding(self) -> None:
        node = MOCK_HOLDINGS_RESPONSE["portfolio"]["aggregateHoldings"]["edges"][0]["node"]
        h = Holding.from_api(node)
        assert h is not None
        assert h.id == "hold_1"
        assert h.total_value == 18127.73
        assert h.security.ticker == "VTSAX"

    def test_none_security(self) -> None:
        node = MOCK_HOLDINGS_RESPONSE["portfolio"]["aggregateHoldings"]["edges"][2]["node"]
        h = Holding.from_api(node)
        assert h is None


class TestAccountHoldings:
    def test_from_api_filters_none_security(self) -> None:
        account_raw = MOCK_ACCOUNTS_RESPONSE["accounts"][3]  # brokerage
        ah = AccountHoldings.from_api(account_raw, MOCK_HOLDINGS_RESPONSE)
        # 3 edges, but one has security=None, so only 2 holdings
        assert len(ah.holdings) == 2


# ---------------------------------------------------------------------------
# Recurring transaction models
# ---------------------------------------------------------------------------


class TestRecurringTransaction:
    def test_valid_item(self) -> None:
        raw = MOCK_RECURRING_RESPONSE["recurringTransactionItems"][0]
        r = RecurringTransaction.from_api(raw)
        assert r is not None
        assert r.merchant_name == "Netflix"
        assert r.amount == -15.99
        assert r.date == "2026-01-15"

    def test_none_merchant(self) -> None:
        raw = MOCK_RECURRING_RESPONSE["recurringTransactionItems"][1]
        r = RecurringTransaction.from_api(raw)
        assert r is not None
        assert r.merchant_name == "Unknown"

    def test_missing_date(self) -> None:
        r = RecurringTransaction.from_api({"amount": -10.0})
        assert r is None


# ---------------------------------------------------------------------------
# MonarchData container
# ---------------------------------------------------------------------------


class TestMonarchData:
    def test_defaults(self) -> None:
        d = MonarchData()
        assert d.accounts == []
        assert d.categories == []
        assert d.credit_history is None
        assert d.holdings == []
        assert d.recurring == []

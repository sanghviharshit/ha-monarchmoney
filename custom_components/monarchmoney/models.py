"""Typed dataclass models for Monarch Money API responses.

Each model provides a ``from_api()`` classmethod that safely parses the raw
JSON dicts returned by the monarchmoney library.  This module is a leaf
dependency and MUST NOT import from any other integration module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Account models
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AccountType:
    """Account type (e.g. depository, brokerage)."""

    name: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> AccountType:
        return cls(name=data.get("name", ""))


@dataclass(frozen=True, slots=True)
class Institution:
    """Financial institution linked to an account."""

    name: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Institution:
        return cls(name=data.get("name", ""))


@dataclass(frozen=True, slots=True)
class Account:
    """A single Monarch Money financial account."""

    id: str
    display_name: str
    display_balance: float
    account_type: AccountType
    institution: Institution
    updated_at: str
    include_in_net_worth: bool
    is_hidden: bool
    is_asset: bool

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Account:
        type_data = data.get("type") or {}
        cred = data.get("credential") or {}
        inst_data = cred.get("institution") or {}
        return cls(
            id=data.get("id", ""),
            display_name=data.get("displayName", ""),
            display_balance=data.get("displayBalance", 0.0),
            account_type=AccountType.from_api(type_data),
            institution=Institution.from_api(inst_data),
            updated_at=data.get("updatedAt", ""),
            include_in_net_worth=data.get("includeInNetWorth", False),
            is_hidden=data.get("isHidden", False),
            is_asset=data.get("isAsset", True),
        )


# ---------------------------------------------------------------------------
# Category models
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CategoryGroup:
    """Category group — either 'income' or 'expense'."""

    type: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> CategoryGroup:
        return cls(type=data.get("type", ""))


@dataclass(frozen=True, slots=True)
class TransactionCategory:
    """A transaction category with its parent group."""

    name: str
    group: CategoryGroup

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> TransactionCategory:
        group_data = data.get("group") or {}
        return cls(
            name=data.get("name", ""),
            group=CategoryGroup.from_api(group_data),
        )


# ---------------------------------------------------------------------------
# Cashflow models
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CashflowSummary:
    """Monthly cashflow summary figures."""

    savings: float
    sum_income: float
    sum_expense: float
    savings_rate: float

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> CashflowSummary:
        return cls(
            savings=data.get("savings", 0.0),
            sum_income=data.get("sumIncome", 0.0),
            sum_expense=data.get("sumExpense", 0.0),
            savings_rate=data.get("savingsRate", 0.0),
        )


@dataclass(frozen=True, slots=True)
class CashflowByCategory:
    """Cashflow total for a single category."""

    category_name: str
    category_group_type: str
    total: float

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> CashflowByCategory:
        group_by = data.get("groupBy") or {}
        category = group_by.get("category") or {}
        group = category.get("group") or {}
        summary = data.get("summary") or {}
        return cls(
            category_name=category.get("name", ""),
            category_group_type=group.get("type", ""),
            total=summary.get("sum", 0.0),
        )


@dataclass(frozen=True, slots=True)
class CashflowData:
    """Complete cashflow response wrapper."""

    summary: CashflowSummary | None
    by_category: list[CashflowByCategory]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> CashflowData:
        summary_list = data.get("summary") or []
        summary: CashflowSummary | None = None
        if summary_list:
            inner = summary_list[0].get("summary") or {}
            summary = CashflowSummary.from_api(inner)
        by_cat_raw = data.get("byCategory") or []
        return cls(
            summary=summary,
            by_category=[CashflowByCategory.from_api(item) for item in by_cat_raw],
        )


# ---------------------------------------------------------------------------
# Credit history models
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CreditScoreSnapshot:
    """A single credit score data point."""

    user_id: str
    score: int
    reported_date: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> CreditScoreSnapshot:
        user = data.get("user") or {}
        return cls(
            user_id=user.get("id", ""),
            score=data.get("score", 0),
            reported_date=data.get("reportedDate", ""),
        )


@dataclass(frozen=True, slots=True)
class HouseholdUser:
    """A user in the Monarch household."""

    id: str
    display_name: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> HouseholdUser:
        return cls(
            id=data.get("id", ""),
            display_name=data.get("displayName", data.get("name", "")),
        )


@dataclass(frozen=True, slots=True)
class CreditHistory:
    """Credit history response wrapper."""

    snapshots: list[CreditScoreSnapshot]
    household_users: list[HouseholdUser]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> CreditHistory:
        snaps_raw = data.get("creditScoreSnapshots") or []
        household = data.get("myHousehold") or {}
        users_raw = household.get("users") or []
        return cls(
            snapshots=[CreditScoreSnapshot.from_api(s) for s in snaps_raw],
            household_users=[HouseholdUser.from_api(u) for u in users_raw],
        )


# ---------------------------------------------------------------------------
# Holdings models
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Security:
    """Security details for a held investment."""

    ticker: str
    name: str
    current_price: float
    type_display: str
    one_day_change_percent: float
    one_day_change_dollars: float

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Security:
        return cls(
            ticker=data.get("ticker", ""),
            name=data.get("name", ""),
            current_price=data.get("currentPrice", 0.0),
            type_display=data.get("typeDisplay", ""),
            one_day_change_percent=data.get("oneDayChangePercent", 0.0),
            one_day_change_dollars=data.get("oneDayChangeDollars", 0.0),
        )


@dataclass(frozen=True, slots=True)
class Holding:
    """A single investment holding."""

    id: str
    total_value: float
    quantity: float
    basis: float
    security: Security

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Holding | None:
        """Return a Holding or None when required security data is missing."""
        sec_data = data.get("security")
        if not sec_data:
            return None
        return cls(
            id=data.get("id", ""),
            total_value=data.get("totalValue", 0.0),
            quantity=data.get("quantity", 0.0),
            basis=data.get("basis", 0.0),
            security=Security.from_api(sec_data),
        )


@dataclass(frozen=True, slots=True)
class AccountHoldings:
    """Holdings for a single brokerage account."""

    account: Account
    holdings: list[Holding]

    @classmethod
    def from_api(
        cls, account_data: dict[str, Any], holdings_data: dict[str, Any]
    ) -> AccountHoldings:
        portfolio = holdings_data.get("portfolio") or {}
        agg = portfolio.get("aggregateHoldings") or {}
        edges = agg.get("edges") or []
        holdings: list[Holding] = []
        for edge in edges:
            node = edge.get("node") or {}
            holding = Holding.from_api(node)
            if holding is not None:
                holdings.append(holding)
        return cls(
            account=Account.from_api(account_data),
            holdings=holdings,
        )


# ---------------------------------------------------------------------------
# Recurring transaction models
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class RecurringTransaction:
    """A single recurring transaction item."""

    date: str
    amount: float
    merchant_name: str
    frequency: str
    category_name: str
    account_name: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> RecurringTransaction:
        stream = data.get("stream") or {}
        merchant = stream.get("merchant") or {}
        category = data.get("category") or {}
        account = data.get("account") or {}
        return cls(
            date=data.get("date", ""),
            amount=data.get("amount", 0.0),
            merchant_name=merchant.get("name", ""),
            frequency=stream.get("frequency", ""),
            category_name=category.get("name", ""),
            account_name=account.get("displayName", ""),
        )


# ---------------------------------------------------------------------------
# Top-level data container (mutable — built incrementally by coordinator)
# ---------------------------------------------------------------------------

@dataclass
class MonarchData:
    """Aggregated data fetched by the update coordinator.

    This is the only mutable dataclass; the coordinator populates each field
    as API calls complete.
    """

    accounts: list[Account] = field(default_factory=list)
    categories: list[TransactionCategory] = field(default_factory=list)
    cashflow: CashflowData | None = None
    credit_history: CreditHistory | None = None
    holdings: list[AccountHoldings] = field(default_factory=list)
    recurring: list[RecurringTransaction] = field(default_factory=list)

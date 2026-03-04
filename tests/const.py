"""Constants and mock data for Monarch Money integration tests."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Mock credentials
# ---------------------------------------------------------------------------
MOCK_EMAIL = "test@example.com"
MOCK_PASSWORD = "test-password-123"
MOCK_TOKEN = "mock-jwt-token-abc123"
MOCK_MFA_CODE = "123456"
MOCK_MFA_SECRET = "JBSWY3DPEHPK3PXP"

# ---------------------------------------------------------------------------
# MOCK_ACCOUNTS_RESPONSE
# ---------------------------------------------------------------------------
# Six accounts covering: depository (x2), credit, brokerage,
# hidden depository (isHidden=True, includeInNetWorth=False),
# hidden loan (isHidden=True, includeInNetWorth=False, isAsset=False).
MOCK_ACCOUNTS_RESPONSE: dict = {
    "accounts": [
        {
            "id": "acct_checking_1",
            "displayName": "Primary Checking",
            "displayBalance": 5432.10,
            "includeInNetWorth": True,
            "isHidden": False,
            "isAsset": True,
            "updatedAt": "2025-12-15T10:30:00Z",
            "type": {"name": "depository"},
            "subtype": {"name": "checking"},
            "credential": {
                "institution": {"name": "Test Bank"}
            },
        },
        {
            "id": "acct_savings_2",
            "displayName": "High-Yield Savings",
            "displayBalance": 25000.00,
            "includeInNetWorth": True,
            "isHidden": False,
            "isAsset": True,
            "updatedAt": "2025-12-15T10:30:00Z",
            "type": {"name": "depository"},
            "subtype": {"name": "savings"},
            "credential": {
                "institution": {"name": "Test Bank"}
            },
        },
        {
            "id": "acct_credit_3",
            "displayName": "Rewards Credit Card",
            "displayBalance": 1500.75,
            "includeInNetWorth": True,
            "isHidden": False,
            "isAsset": False,
            "updatedAt": "2025-12-14T08:00:00Z",
            "type": {"name": "credit"},
            "subtype": {"name": "credit_card"},
            "credential": {
                "institution": {"name": "Test Credit Union"}
            },
        },
        {
            "id": "acct_brokerage_4",
            "displayName": "Investment Account",
            "displayBalance": 150000.00,
            "includeInNetWorth": True,
            "isHidden": False,
            "isAsset": True,
            "updatedAt": "2025-12-15T06:00:00Z",
            "type": {"name": "brokerage"},
            "subtype": {"name": "brokerage"},
            "credential": {
                "institution": {"name": "Test Investments"}
            },
        },
        {
            "id": "acct_hidden_dep_5",
            "displayName": "Hidden Checking",
            "displayBalance": 100.00,
            "includeInNetWorth": False,
            "isHidden": True,
            "isAsset": True,
            "updatedAt": "2025-12-10T12:00:00Z",
            "type": {"name": "depository"},
            "subtype": {"name": "checking"},
            "credential": {
                "institution": {"name": "Old Bank"}
            },
        },
        {
            "id": "acct_hidden_loan_6",
            "displayName": "Hidden Auto Loan",
            "displayBalance": 12000.00,
            "includeInNetWorth": False,
            "isHidden": True,
            "isAsset": False,
            "updatedAt": "2025-12-01T00:00:00Z",
            "type": {"name": "loan"},
            "subtype": {"name": "auto"},
            "credential": {
                "institution": {"name": "Auto Finance Co"}
            },
        },
    ]
}

# ---------------------------------------------------------------------------
# MOCK_CATEGORIES_RESPONSE
# ---------------------------------------------------------------------------
MOCK_CATEGORIES_RESPONSE: dict = {
    "categories": [
        {
            "id": "cat_salary",
            "name": "Salary",
            "group": {"id": "grp_income", "type": "income", "name": "Income"},
        },
        {
            "id": "cat_freelance",
            "name": "Freelance",
            "group": {"id": "grp_income", "type": "income", "name": "Income"},
        },
        {
            "id": "cat_groceries",
            "name": "Groceries",
            "group": {"id": "grp_expense", "type": "expense", "name": "Food & Drink"},
        },
        {
            "id": "cat_rent",
            "name": "Rent",
            "group": {"id": "grp_expense", "type": "expense", "name": "Housing"},
        },
        {
            "id": "cat_utilities",
            "name": "Utilities",
            "group": {"id": "grp_expense", "type": "expense", "name": "Housing"},
        },
        {
            "id": "cat_entertainment",
            "name": "Entertainment",
            "group": {"id": "grp_expense", "type": "expense", "name": "Entertainment"},
        },
    ]
}

# ---------------------------------------------------------------------------
# MOCK_CASHFLOW_RESPONSE
# ---------------------------------------------------------------------------
MOCK_CASHFLOW_RESPONSE: dict = {
    "summary": [
        {
            "summary": {
                "savings": 1200.50,
                "sumIncome": 6500.00,
                "sumExpense": -5299.50,
                "savingsRate": 0.1847,
            }
        }
    ],
    "byCategory": [
        {
            "groupBy": {
                "category": {
                    "id": "cat_salary",
                    "name": "Salary",
                    "group": {"id": "grp_income", "type": "income", "name": "Income"},
                }
            },
            "summary": {"sum": 6000.00, "count": 2},
        },
        {
            "groupBy": {
                "category": {
                    "id": "cat_freelance",
                    "name": "Freelance",
                    "group": {"id": "grp_income", "type": "income", "name": "Income"},
                }
            },
            "summary": {"sum": 500.00, "count": 1},
        },
        {
            "groupBy": {
                "category": {
                    "id": "cat_groceries",
                    "name": "Groceries",
                    "group": {
                        "id": "grp_expense",
                        "type": "expense",
                        "name": "Food & Drink",
                    },
                }
            },
            "summary": {"sum": -850.25, "count": 15},
        },
        {
            "groupBy": {
                "category": {
                    "id": "cat_rent",
                    "name": "Rent",
                    "group": {
                        "id": "grp_expense",
                        "type": "expense",
                        "name": "Housing",
                    },
                }
            },
            "summary": {"sum": -2200.00, "count": 1},
        },
        {
            "groupBy": {
                "category": {
                    "id": "cat_utilities",
                    "name": "Utilities",
                    "group": {
                        "id": "grp_expense",
                        "type": "expense",
                        "name": "Housing",
                    },
                }
            },
            "summary": {"sum": -350.00, "count": 3},
        },
        {
            "groupBy": {
                "category": {
                    "id": "cat_entertainment",
                    "name": "Entertainment",
                    "group": {
                        "id": "grp_expense",
                        "type": "expense",
                        "name": "Entertainment",
                    },
                }
            },
            "summary": {"sum": -1899.25, "count": 8},
        },
    ],
}

# ---------------------------------------------------------------------------
# MOCK_CREDIT_RESPONSE
# ---------------------------------------------------------------------------
# Matches get_credit_history() response shape:
#   creditScoreSnapshots[].user.id, .score, .reportedDate
#   myHousehold.users[].id, .displayName, .name
MOCK_CREDIT_RESPONSE: dict = {
    "creditScoreSnapshots": [
        {"user": {"id": "user_1"}, "score": 780, "reportedDate": "2025-12-01"},
        {"user": {"id": "user_1"}, "score": 775, "reportedDate": "2025-11-01"},
        {"user": {"id": "user_1"}, "score": 770, "reportedDate": "2025-10-01"},
        {"user": {"id": "user_2"}, "score": 720, "reportedDate": "2025-12-01"},
        {"user": {"id": "user_2"}, "score": 715, "reportedDate": "2025-11-01"},
    ],
    "myHousehold": {
        "users": [
            {"id": "user_1", "displayName": "Alice Test", "name": "Alice Test"},
            {"id": "user_2", "displayName": "Bob Test", "name": "Bob Test"},
        ]
    },
}

# ---------------------------------------------------------------------------
# MOCK_RECURRING_RESPONSE
# ---------------------------------------------------------------------------
# Matches get_recurring_transactions() response shape:
#   recurringTransactionItems[].date, .amount, .stream.merchant.name,
#   .stream.frequency, .category.name, .account.displayName
MOCK_RECURRING_RESPONSE: dict = {
    "recurringTransactionItems": [
        {
            "date": "2026-01-15",
            "amount": -15.99,
            "stream": {
                "merchant": {"name": "Netflix"},
                "frequency": "monthly",
            },
            "category": {"name": "Entertainment"},
            "account": {"displayName": "Rewards Credit Card"},
        },
        {
            "date": "2026-01-01",
            "amount": -2200.00,
            "stream": {
                "merchant": None,
                "frequency": "monthly",
            },
            "category": {"name": "Rent"},
            "account": {"displayName": "Primary Checking"},
        },
        {
            "date": "2026-01-10",
            "amount": 3000.00,
            "stream": {
                "merchant": {"name": "Acme Corp"},
                "frequency": "biweekly",
            },
            "category": {"name": "Salary"},
            "account": {"displayName": "Primary Checking"},
        },
    ]
}

# ---------------------------------------------------------------------------
# MOCK_HOLDINGS_RESPONSE
# ---------------------------------------------------------------------------
# Matches get_account_holdings(id) response shape:
#   portfolio.aggregateHoldings.edges[].node.{id, totalValue, quantity, basis,
#   security.{ticker, name, currentPrice, typeDisplay, oneDayChangePercent, oneDayChangeDollars}}
MOCK_HOLDINGS_RESPONSE: dict = {
    "portfolio": {
        "aggregateHoldings": {
            "edges": [
                {
                    "node": {
                        "id": "hold_1",
                        "totalValue": 18127.73,
                        "quantity": 150.5,
                        "basis": 15000.00,
                        "security": {
                            "ticker": "VTSAX",
                            "name": "Vanguard Total Stock Market Index Fund",
                            "currentPrice": 120.45,
                            "typeDisplay": "Mutual Fund",
                            "oneDayChangePercent": 0.35,
                            "oneDayChangeDollars": 0.42,
                        },
                    }
                },
                {
                    "node": {
                        "id": "hold_2",
                        "totalValue": 4887.50,
                        "quantity": 25.0,
                        "basis": 3500.00,
                        "security": {
                            "ticker": "AAPL",
                            "name": "Apple Inc.",
                            "currentPrice": 195.50,
                            "typeDisplay": "Stock",
                            "oneDayChangePercent": -0.15,
                            "oneDayChangeDollars": -0.29,
                        },
                    }
                },
                {
                    "node": {
                        "id": "hold_3",
                        "totalValue": 50000.00,
                        "quantity": 1.0,
                        "basis": 50000.00,
                        "security": None,
                    }
                },
            ]
        }
    }
}

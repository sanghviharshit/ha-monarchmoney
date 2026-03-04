"""Constants for Monarch Money sensor platform."""

ATTR_ASSETS = "ASSETS"
ATTR_LIABILITIES = "LIABILITIES"

ATTR_BROKERAGE = "Investments"
ATTR_CREDIT = "Credit Cards"
ATTR_DEPOSITORY = "Cash"
ATTR_LOAN = "Loans"
ATTR_OTHER = "Other"
ATTR_REAL_ESTATE = "Real Estate"
ATTR_VALUABLE = "Valuables"
ATTR_VEHICLE = "Vehicles"
ATTR_OTHER_ASSET = "Other Assets"
ATTR_OTHER_LIABILITY = "Other Liabilities"

SENSOR_TYPES_GROUP: dict[str, dict[str, str]] = {
    ATTR_BROKERAGE: {
        "type": "brokerage",
        "group": ATTR_ASSETS,
        "icon": "mdi:chart-line",
    },
    ATTR_CREDIT: {
        "type": "credit",
        "group": ATTR_LIABILITIES,
        "icon": "mdi:credit-card",
    },
    ATTR_DEPOSITORY: {"type": "depository", "group": ATTR_ASSETS, "icon": "mdi:cash"},
    ATTR_LOAN: {"type": "loan", "group": ATTR_LIABILITIES, "icon": "mdi:bank"},
    ATTR_OTHER: {"type": "other", "group": "OTHER", "icon": "mdi:information-outline"},
    ATTR_REAL_ESTATE: {"type": "real_estate", "group": ATTR_ASSETS, "icon": "mdi:home"},
    ATTR_VALUABLE: {
        "type": "valuables",
        "group": ATTR_ASSETS,
        "icon": "mdi:treasure-chest",
    },
    ATTR_VEHICLE: {"type": "vehicle", "group": ATTR_ASSETS, "icon": "mdi:car"},
    ATTR_OTHER_ASSET: {
        "type": "other_asset",
        "group": ATTR_ASSETS,
        "icon": "mdi:file-document-outline",
    },
    ATTR_OTHER_LIABILITY: {
        "type": "other_liability",
        "group": ATTR_LIABILITIES,
        "icon": "mdi:account-alert-outline",
    },
}

# Prefix for entity names based on account group
GROUP_PREFIX: dict[str, str] = {
    ATTR_ASSETS: "Assets",
    ATTR_LIABILITIES: "Liabilities",
    "OTHER": "Accounts",
}

# Override display name for categories where the raw name is redundant with the prefix
CATEGORY_DISPLAY_OVERRIDE: dict[str, str] = {
    ATTR_OTHER_ASSET: "Other",
    ATTR_OTHER_LIABILITY: "Other",
}

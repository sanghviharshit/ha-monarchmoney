"""Constants for the Monarch Money integration."""

from homeassistant.const import Platform

DOMAIN = "monarchmoney"

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BUTTON,
    Platform.CALENDAR,
]

ATTRIBUTION = "Data provided by Monarch"

CONF_TIMEOUT = "timeout"
CONF_TOKEN = "token"
CONF_MFA_CODE = "mfa_code"
CONF_MFA_SECRET = "mfa_secret"
CONF_ENABLE_RECURRING = "enable_recurring"
CONF_ENABLE_CREDIT_SCORE = "enable_credit_score"
CONF_ENABLE_HOLDINGS = "enable_holdings"
CONF_ENABLE_AGGREGATED_HOLDINGS = "enable_aggregated_holdings"

VALUES_SCAN_INTERVAL = {
    60: "60 minutes (1 hour)",
    120: "120 minutes (2 hours)",
    240: "240 minutes (4 hours)",
    360: "360 minutes (6 hours)",
    720: "720 minutes (12 hours)",
    1440: "1440 minutes (24 hours)",
}
VALUES_TIMEOUT = {
    10: "10 seconds",
    15: "15 seconds",
    30: "30 seconds",
    45: "45 seconds",
    60: "60 seconds",
}

DEFAULT_SCAN_INTERVAL = 60
DEFAULT_TIMEOUT = 30

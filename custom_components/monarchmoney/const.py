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

VALUES_SCAN_INTERVAL = [60, 120, 600, 1800, 3600, 21600, 86400]
VALUES_TIMEOUT = [10, 15, 30, 45, 60]

DEFAULT_SCAN_INTERVAL = VALUES_SCAN_INTERVAL[4]
DEFAULT_TIMEOUT = VALUES_TIMEOUT[2]

"""Constants for the Monarch Money integration."""

DOMAIN = "monarchmoney"

ATTRIBUTION = "Data provided by Monarch"
SESSION_FILE = ".mm-session.pickle"

CONF_TIMEOUT = "timeout"

VALUES_SCAN_INTERVAL = [60, 120, 600, 1800, 3600, 21600, 86400]
VALUES_TIMEOUT = [10, 15, 30, 45, 60]

DEFAULT_SCAN_INTERVAL = VALUES_SCAN_INTERVAL[4]
DEFAULT_TIMEOUT = VALUES_TIMEOUT[2]

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.1] - 2026-07-31

### Fixed
- **Blocking I/O in the event loop** - bumped `monarchmoneycommunity` from 1.3.0 to 1.5.1. The 1.3.0 library ran `importlib.metadata.version("gql")` on every GraphQL call, triggering synchronous disk reads (`os.listdir`, `read_text`, `open`) inside the asyncio event loop. This blocked Home Assistant long enough to cause timeouts across other integrations and Supervisor Watchdog restarts. The offending check was removed upstream in 1.5.1. (#23)

---

## [2.1.0] - 2026-03-06

### Changed
- **Options flow dropdown selectors** - Scan interval and timeout options now use dropdown selectors with human-readable labels (e.g. "60 minutes (1 hour)") instead of raw integer lists
- **Scan interval units changed to minutes** - scan interval is now configured in minutes instead of seconds; existing configs with second-based values (>1440) are automatically migrated
- **Options labels clarified** - "Scan Interval" → "Scan Interval (minutes)", "Timeout" → "Timeout (seconds)"
- **Updated scan interval options** - 60, 120, 240, 360, 720, 1440 minutes (previously 60 to 86400 seconds)
- Default scan interval changed from 3600 seconds to 60 minutes (same effective duration)

---

## [2.0.0] - 2026-03-03

### Added
- **Summary Total Assets / Total Liabilities sensors** - two new always-on sensors (`Summary Total Assets`, `Summary Total Liabilities`) that report the sum of asset and liability accounts respectively (filtered by `include_in_net_worth` and `is_hidden`), each with an `account_count` attribute
- **Typed data models** (`models.py`) - dataclasses for `Account`, `CashflowSummary`, `TransactionCategory`, `Holding`, `RecurringTransaction`, etc., with `from_api()` factory methods replacing raw API dicts
- **Shared entity base** (`entity.py`) - extracted `MonarchEntity` base class for consistent device info and naming
- **Config entry migration** - `async_migrate_entry` handles v1 → v2 config entry upgrades automatically
- **Comprehensive test suite** - `test_models.py`, `test_sensors.py`, `test_coordinator.py`, `test_config_flow.py`, `test_calendar.py`, `test_button.py` with shared fixtures and mock API responses
- **CI workflows** - hassfest validation, HACS validation, and pytest run on push/PR

### Changed
- **Sensor module split** - decomposed monolithic `sensor.py` (972 lines) into `sensor/` package: `net_worth`, `cashflow`, `income`, `expense`, `category`, `holding`, `aggregated_holding`, `credit_score`
- `AccountHoldings.from_api` now accepts `Account` objects directly instead of reconstructing raw dicts
- `TransactionCategory.group` is now nullable; all sensor code guards against `None`
- `RecurringTransaction.from_api` returns `None` for entries with missing dates (skipped during parsing)
- `HouseholdUser.display_name` and `RecurringTransaction.merchant_name` default to `"Unknown"` instead of empty string
- Coordinator uses walrus operator for cleaner recurring transaction filtering

### Fixed
- **Button error handling** - raises `HomeAssistantError` instead of silently returning on failure
- **Config flow network errors** - catches `ConnectionError`/`TimeoutError`/`OSError` and shows `cannot_connect` form error
- **`asyncio.CancelledError` swallowed** - coordinator auth flows now re-raise instead of catching all exceptions
- **Net worth double-counting** - liabilities are now filtered by `include_in_net_worth`/`is_hidden`, matching asset filtering
- **Cashflow null safety** - sensors guard against missing `data.cashflow` to avoid `AttributeError`

---

## [1.5.0] - 2026-03-02

### Added
- **Credit score sensors** (optional) - per-household-member credit score with `reported_date`, `previous_score`, and `score_change` attributes; enable via Options
- **Investment holding sensors** (optional) - per-security value within each brokerage account, including quantity, cost basis, and gain/loss; enable via Options
- **Aggregated holding sensors** (optional) - total position per ticker aggregated across all brokerage accounts; enable via Options
- **Recurring transactions calendar** (optional) - upcoming bills and subscriptions as HA calendar events (current month + next month window); enable via Options
- **Refresh button** - manually trigger account refresh from institutions without waiting for the next poll cycle
- Four new options in the config Options flow: `Enable Credit Score`, `Enable Investment Holdings (per account)`, `Enable Aggregated Investment Holdings`, `Enable Recurring Transactions Calendar`

### Changed
- Core API calls (`get_accounts`, `get_transaction_categories`, `get_cashflow`) are now fetched in parallel, reducing poll latency
- Optional data (credit history, recurring) also fetched in parallel with isolated per-task error handling
- Sensor display names updated for clarity:
  - `Cash Flow` → `Cashflow Savings This Month`
  - `Income` → `Cashflow Income This Month`
  - `Expenses` → `Cashflow Expenses This Month`
  - `Net Worth` → `Summary Net Worth`
  - Account category sensors now prefixed with their group (e.g. `Assets Cash`, `Liabilities Credit Cards`)
- Device name shortened from `"Monarch Money"` to `"Monarch"` across all entities
- README rewritten with feature list, updated install/setup steps, and options configuration table

### Fixed
- Disabling an optional feature in Options now removes stale entity registry entries (no more ghost entities for credit score, holdings, or recurring calendar)

### Migration notes
- The unique IDs for three cashflow sensors changed; legacy entries are auto-removed on first load after upgrade. Any automations or dashboards referencing `sensor.monarch_cash_flow`, `sensor.monarch_income`, or `sensor.monarch_expense` will need to be updated to the new entity IDs.

---

## [1.4.0] - 2026-02-28

### Fixed
- Fixed issue [#16](https://github.com/sanghviharshit/ha-monarchmoney/issues/16): session file creation in Docker environments by disabling session save/reuse in `monarch_login()` helper

---

## [1.3.0] - 2026-02-27

### Added
- `util.py` with shared `monarch_login()` helper (disables session saving/reuse) and `format_date()` utility
- Re-authentication flow with 60-second cooldown between attempts to avoid rate limiting
- `_is_mfa_error()` and `_update_mfa_secret()` extracted as testable helpers in `config_flow.py`

### Changed
- Major refactor: all modules now follow standard HA patterns (`_attr_*`, `CoordinatorEntity`, `_attr_has_entity_name`)
- Config flow (VERSION bumped to 2) simplified and cleaned up; removed redundant session-save logic after login
- Coordinator rewritten: session validation on startup, auth retry with TOTP auto-refresh
- Sensor unique IDs now stable: format `monarchmoney_{email}_{sensor_suffix}`
- Logging switched from f-strings to `%`-style format strings
- `manifest.json` updated to `monarchmoneycommunity==1.3.0`
- `strings.json` and `translations/en.json` brought back into sync

### Removed
- `util.py` helper removed (re-added in different form; session-save calls removed from config flow)

---

## [1.2.0] - 2026-02-26

### Changed
- Switched API dependency from `monarchmoney` to `monarchmoneycommunity` (community-maintained fork) - `monarchmoneycommunity==1.3.0`

---

## [1.1.0] - 2025-07-22

### Changed
- Version bump to `1.1.0` in `manifest.json`

---

## [1.0.0] - 2025-07-11

### Added
- **Multi-factor authentication (MFA) support** - manual code entry during config flow, plus automatic TOTP via stored secret key (auto-refreshes on session expiry)
- Re-authentication flow (`reauth`) surfaced in UI when credentials become invalid
- MFA step detection via `RequireMFAException`
- `strings.json` and `translations/en.json` extended with MFA and re-auth UI strings

---

## [0.0.5] - 2025-07-11

### Added
- `DataUpdateCoordinator` introduced; sensors now update reactively instead of polling individually
- Options flow: configurable scan interval and API timeout
- Income and expense per-category breakdowns as `extra_state_attributes`
- Cash flow (savings) sensor
- Net worth sensor with assets/liabilities breakdown

### Fixed
- Improved error handling in sensor updates and coordinator fetches
- Sensors now show `Unknown` on initial load rather than `0`

---

## [0.0.4] - 2025-01-31

### Changed
- Updated `monarchmoney` Python package dependency to latest version

---

## [0.0.3] - 2024-06-28

### Changed
- Renamed sensor state attributes for consistency

---

## [0.0.2] - 2024-01-30

### Fixed
- Expense sensor values are now reported as positive numbers (negated before storage)

---

## [0.0.1] - 2023-04-17

### Added
- Initial release: account balance sensors grouped by account type, net worth sensor, basic config flow with email/password login

[Unreleased]: https://github.com/sanghviharshit/ha-monarchmoney/compare/2.1.1...HEAD
[2.1.1]: https://github.com/sanghviharshit/ha-monarchmoney/compare/2.1.0...2.1.1
[2.1.0]: https://github.com/sanghviharshit/ha-monarchmoney/compare/2.0.0...2.1.0
[2.0.0]: https://github.com/sanghviharshit/ha-monarchmoney/compare/1.5.0...2.0.0
[1.5.0]: https://github.com/sanghviharshit/ha-monarchmoney/compare/1.4.0...1.5.0
[1.4.0]: https://github.com/sanghviharshit/ha-monarchmoney/compare/1.3.0...1.4.0
[1.3.0]: https://github.com/sanghviharshit/ha-monarchmoney/compare/1.2.0...1.3.0
[1.2.0]: https://github.com/sanghviharshit/ha-monarchmoney/compare/1.1.0...1.2.0
[1.1.0]: https://github.com/sanghviharshit/ha-monarchmoney/compare/1.0.0...1.1.0
[1.0.0]: https://github.com/sanghviharshit/ha-monarchmoney/compare/0.0.5...1.0.0
[0.0.5]: https://github.com/sanghviharshit/ha-monarchmoney/compare/0.0.4...0.0.5
[0.0.4]: https://github.com/sanghviharshit/ha-monarchmoney/compare/0.0.3...0.0.4
[0.0.3]: https://github.com/sanghviharshit/ha-monarchmoney/compare/0.0.2...0.0.3
[0.0.2]: https://github.com/sanghviharshit/ha-monarchmoney/compare/0.0.1...0.0.2
[0.0.1]: https://github.com/sanghviharshit/ha-monarchmoney/releases/tag/0.0.1

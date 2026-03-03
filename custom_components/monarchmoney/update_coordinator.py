"""Update coordinator for Monarch Money integration."""

import asyncio
import calendar as cal_module
from datetime import date, timedelta
import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from monarchmoney import MonarchMoney, RequireMFAException

from .const import (
    CONF_ENABLE_AGGREGATED_HOLDINGS,
    CONF_ENABLE_CREDIT_SCORE,
    CONF_ENABLE_HOLDINGS,
    CONF_ENABLE_RECURRING,
    CONF_MFA_SECRET,
    CONF_TOKEN,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
)
from .models import (
    Account,
    AccountHoldings,
    CashflowData,
    CreditHistory,
    MonarchData,
    RecurringTransaction,
    TransactionCategory,
)
from .util import monarch_login

_LOGGER = logging.getLogger(__name__)


class MonarchCoordinator(DataUpdateCoordinator[MonarchData]):
    """Monarch Money data update coordinator."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        # Initialize with stored token if available (no pickle file needed)
        stored_token = config_entry.data.get(CONF_TOKEN)
        self._api = MonarchMoney(token=stored_token) if stored_token else MonarchMoney()
        self._auth_lock = (
            asyncio.Lock()
        )  # Prevent concurrent re-authentication attempts
        self._last_auth_attempt: float = (
            0  # Track last authentication attempt for rate limiting
        )

        options = config_entry.options
        self._update_interval: int = options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        self._timeout: int = options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)

        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=DOMAIN,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=self._update_interval),
            config_entry=config_entry,
        )

    @property
    def api(self) -> MonarchMoney:
        """Return the API client."""
        return self._api

    async def _async_setup(self) -> None:
        """Set up session on first refresh (called automatically)."""
        _LOGGER.debug("Setting up coordinator session")

        # Validate existing token from config entry
        if self.config_entry.data.get(CONF_TOKEN):
            if await self._validate_session():
                _LOGGER.debug("Stored token is valid")
                return
            _LOGGER.debug("Stored token is invalid, will re-authenticate")

        _LOGGER.debug("Attempting authentication with stored credentials")
        if await self._authenticate_with_credentials():
            _LOGGER.info("Initial authentication successful during setup")
        else:
            _LOGGER.warning("Initial authentication failed during setup")

    async def _validate_session(self) -> bool:
        """Check if the current session is valid by making a lightweight API call."""
        try:
            # Make a simple API call to check if session is valid
            await self._api.get_subscription_details()
            return True
        except Exception as err:
            _LOGGER.debug("Session validation failed: %s", err)
            return False

    async def _authenticate_with_credentials(self) -> bool:
        """Authenticate using stored credentials."""
        async with self._auth_lock:
            # Rate limiting: don't attempt re-authentication more than once per minute
            current_time = time.time()
            if current_time - self._last_auth_attempt < 60:
                _LOGGER.debug(
                    "Rate limiting: skipping re-authentication (last attempt was %.0f seconds ago)",
                    current_time - self._last_auth_attempt,
                )
                return False

            self._last_auth_attempt = current_time

            try:
                config_data = self.config_entry.data
                email = config_data.get(CONF_EMAIL)
                password = config_data.get(CONF_PASSWORD)

                if not email or not password:
                    _LOGGER.error("Missing email or password in config entry")
                    return False

                _LOGGER.debug("Attempting to authenticate with stored credentials")

                mfa_secret = config_data.get(CONF_MFA_SECRET)

                # Create a fresh API instance for re-authentication to avoid state issues
                fresh_api = MonarchMoney()
                await monarch_login(fresh_api, email, password, mfa_secret)
                _LOGGER.info("Successfully authenticated")

                # Replace the old API instance with the fresh authenticated one
                self._api = fresh_api

                # Persist the new token in the config entry (no pickle file needed)
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={**self.config_entry.data, CONF_TOKEN: fresh_api.token},
                )

                return True

            except RequireMFAException:
                _LOGGER.warning(
                    "MFA required but no valid MFA secret stored. User needs to reconfigure."
                )
                return False
            except Exception as err:
                _LOGGER.error("Failed to authenticate with stored credentials: %s", err)
                return False

    async def _fetch_api_data(self) -> MonarchData:
        """Fetch all data sets from the Monarch API."""
        data = MonarchData()
        options = self.config_entry.options

        # Core data (always fetched in parallel)
        accounts_raw, categories_raw, cashflow_raw = await asyncio.gather(
            self._api.get_accounts(),
            self._api.get_transaction_categories(),
            self._api.get_cashflow(),
        )

        data.accounts = [
            Account.from_api(a) for a in accounts_raw.get("accounts") or []
        ]
        data.categories = [
            TransactionCategory.from_api(c)
            for c in categories_raw.get("categories") or []
        ]
        data.cashflow = CashflowData.from_api(cashflow_raw or {})
        _LOGGER.debug(
            "Fetched %d accounts, %d categories from API",
            len(data.accounts),
            len(data.categories),
        )

        # Optional data groups (only if enabled)
        optional_tasks: dict[str, asyncio.Task] = {}

        if options.get(CONF_ENABLE_CREDIT_SCORE, False):
            optional_tasks["credit_history"] = self._api.get_credit_history()

        if options.get(CONF_ENABLE_RECURRING, False):
            today = date.today()
            start = today.replace(day=1)
            # End of next month
            if today.month == 12:
                next_month = today.replace(year=today.year + 1, month=1, day=1)
            else:
                next_month = today.replace(month=today.month + 1, day=1)
            _, last_day = cal_module.monthrange(next_month.year, next_month.month)
            end = next_month.replace(day=last_day)
            optional_tasks["recurring"] = self._api.get_recurring_transactions(
                start_date=start.strftime("%Y-%m-%d"),
                end_date=end.strftime("%Y-%m-%d"),
            )

        if optional_tasks:
            keys = list(optional_tasks.keys())
            results = await asyncio.gather(
                *optional_tasks.values(), return_exceptions=True
            )
            for key, result in zip(keys, results):
                if isinstance(result, Exception):
                    _LOGGER.error("Failed to fetch %s: %s", key, result)
                elif key == "credit_history":
                    data.credit_history = CreditHistory.from_api(result)
                elif key == "recurring":
                    items = result.get("recurringTransactionItems") or []
                    data.recurring = [
                        r for r in (RecurringTransaction.from_api(i) for i in items)
                        if r is not None
                    ]

        # Holdings: one call per brokerage account (opt-in)
        if options.get(CONF_ENABLE_HOLDINGS, False) or options.get(
            CONF_ENABLE_AGGREGATED_HOLDINGS, False
        ):
            brokerage_accounts = [
                a
                for a in data.accounts
                if a.account_type.name == "brokerage" and not a.is_hidden
            ]
            if brokerage_accounts:
                holdings_results = await asyncio.gather(
                    *(
                        self._api.get_account_holdings(int(a.id))
                        for a in brokerage_accounts
                    ),
                    return_exceptions=True,
                )
                for account, result in zip(brokerage_accounts, holdings_results):
                    if isinstance(result, Exception):
                        _LOGGER.error(
                            "Failed to fetch holdings for %s: %s",
                            account.display_name,
                            result,
                        )
                    else:
                        # Build raw account dict for AccountHoldings.from_api
                        account_raw = {
                            "id": account.id,
                            "displayName": account.display_name,
                            "displayBalance": account.display_balance,
                            "type": {"name": account.account_type.name},
                            "credential": {
                                "institution": {"name": account.institution.name}
                            },
                            "updatedAt": account.updated_at,
                            "includeInNetWorth": account.include_in_net_worth,
                            "isHidden": account.is_hidden,
                            "isAsset": account.is_asset,
                        }
                        data.holdings.append(
                            AccountHoldings.from_api(account_raw, result)
                        )
                _LOGGER.debug(
                    "Fetched holdings for %d brokerage accounts",
                    len(data.holdings),
                )

        return data

    @staticmethod
    def _is_auth_error(err: Exception) -> bool:
        """Check if an exception indicates an authentication error."""
        error_str = str(err).lower()
        return any(
            keyword in error_str
            for keyword in ("unauthorized", "authentication", "401")
        )

    async def _async_update_data(self) -> MonarchData:
        """Fetch data from API endpoint."""
        try:
            async with asyncio.timeout(self._timeout):
                try:
                    return await self._fetch_api_data()
                except RequireMFAException as err:
                    _LOGGER.error("MFA required for Monarch Money authentication")
                    raise ConfigEntryAuthFailed(
                        "Multi-factor authentication required. Please reconfigure the integration."
                    ) from err
                except Exception as err:
                    _LOGGER.error("Error fetching data from Monarch API: %s", err)
                    if self._is_auth_error(err):
                        _LOGGER.info(
                            "Authentication failed, attempting to re-authenticate"
                        )
                        if await self._authenticate_with_credentials():
                            _LOGGER.info(
                                "Re-authentication successful, retrying data fetch"
                            )
                            try:
                                return await self._fetch_api_data()
                            except Exception as retry_err:
                                _LOGGER.error(
                                    "Data fetch failed after re-authentication: %s",
                                    retry_err,
                                )
                                raise ConfigEntryAuthFailed(
                                    f"Authentication failed: {retry_err}"
                                ) from retry_err
                        else:
                            _LOGGER.error(
                                "Re-authentication failed, triggering config flow"
                            )
                            raise ConfigEntryAuthFailed(
                                f"Authentication failed: {err}"
                            ) from err
                    raise UpdateFailed(
                        f"Error communicating with API: {err}"
                    ) from err
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

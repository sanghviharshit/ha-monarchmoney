"""Update coordinator for Monarch Money integration."""

import asyncio
from datetime import timedelta
import logging
import time
from typing import Any

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
    CONF_MFA_SECRET,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class MonarchCoordinator(DataUpdateCoordinator):
    """Monarch Money data update coordinator."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self._api = MonarchMoney()
        self._auth_lock = (
            asyncio.Lock()
        )  # Prevent concurrent re-authentication attempts
        self._last_auth_attempt = (
            0  # Track last authentication attempt for rate limiting
        )
        # Session loading moved to _async_setup to avoid blocking I/O in event loop

        options = config_entry.options
        self._update_interval = options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        self._timeout = options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)

        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=DOMAIN,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=self._update_interval),
            config_entry=config_entry,
        )

    async def _async_setup(self) -> None:
        """Set up session on first refresh (called automatically)."""
        _LOGGER.debug("Setting up coordinator session")
        mfa_secret = self.config_entry.data.get(CONF_MFA_SECRET)
        _LOGGER.debug(
            "MFA secret available: %s",
            bool(mfa_secret and mfa_secret.strip()),
        )

        # Try to load existing session first
        session_loaded = False
        try:
            await self.hass.async_add_executor_job(self._api.load_session)
            if await self._validate_session():
                _LOGGER.debug("Loaded session is valid")
                session_loaded = True
            else:
                _LOGGER.debug("Loaded session is invalid, will re-authenticate")
        except Exception as err:
            _LOGGER.debug("Failed to load existing session: %s", err)

        if not session_loaded:
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
                _LOGGER.debug("Config entry data keys: %s", list(config_data.keys()))

                # Check if we have a valid MFA secret for automatic authentication
                mfa_secret = config_data.get(CONF_MFA_SECRET)
                _LOGGER.debug(
                    "MFA secret found in config: %s",
                    bool(mfa_secret and mfa_secret.strip()),
                )

                # Create a fresh API instance for re-authentication to avoid state issues
                _LOGGER.debug(
                    "Creating fresh MonarchMoney instance for re-authentication"
                )
                fresh_api = MonarchMoney()

                if mfa_secret and mfa_secret.strip():
                    _LOGGER.debug("Using stored MFA secret for authentication")
                    await fresh_api.login(
                        email=email,
                        password=password,
                        save_session=False,  # Disable automatic session saving to avoid blocking I/O
                        use_saved_session=False,  # Don't use existing session for fresh login
                        mfa_secret_key=mfa_secret.strip(),
                    )
                    _LOGGER.info("Successfully authenticated with MFA secret")
                else:
                    _LOGGER.debug("No valid MFA secret found, attempting regular login")
                    # Try regular login first
                    await fresh_api.login(
                        email=email,
                        password=password,
                        save_session=False,  # Disable automatic session saving to avoid blocking I/O
                        use_saved_session=False,  # Don't use existing session for fresh login
                    )
                    _LOGGER.info("Successfully authenticated with email/password")

                # Replace the old API instance with the fresh authenticated one
                _LOGGER.debug("Replacing API instance with freshly authenticated one")
                self._api = fresh_api

                # Save session manually using executor to avoid blocking I/O
                await self.hass.async_add_executor_job(self._api.save_session)
                _LOGGER.debug("Session saved successfully after re-authentication")

                return True

            except RequireMFAException:
                _LOGGER.warning(
                    "MFA required but no valid MFA secret stored. User needs to reconfigure."
                )
                return False
            except Exception as err:
                _LOGGER.error("Failed to authenticate with stored credentials: %s", err)
                return False

    async def _fetch_api_data(self) -> dict[str, Any]:
        """Fetch all data sets from the Monarch API."""
        data: dict[str, Any] = {"accounts": [], "categories": [], "cashflow": {}}

        accounts = await self._api.get_accounts()
        data["accounts"] = accounts.get("accounts") or []
        _LOGGER.debug("Fetched %d accounts from API", len(data["accounts"]))

        categories = await self._api.get_transaction_categories()
        data["categories"] = categories.get("categories") or []
        _LOGGER.debug("Fetched %d categories from API", len(data["categories"]))

        cashflow = await self._api.get_cashflow()
        data["cashflow"] = cashflow or {}
        _LOGGER.debug("Fetched cashflow data: %s", bool(data["cashflow"]))

        return data

    @staticmethod
    def _is_auth_error(err: Exception) -> bool:
        """Check if an exception indicates an authentication error."""
        error_str = str(err).lower()
        return any(
            keyword in error_str
            for keyword in ("unauthorized", "authentication", "401")
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API endpoint."""
        try:
            async with asyncio.timeout(self._timeout):
                try:
                    data = await self._fetch_api_data()

                    # Debug: log account types for troubleshooting
                    if data["accounts"]:
                        account_types = [
                            acc.get("type", {}).get("name")
                            for acc in data["accounts"]
                            if acc.get("type")
                        ]
                        _LOGGER.debug("Account types found: %s", set(account_types))

                    return data
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

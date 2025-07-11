"""Update coordinator for Monarch Money integration."""

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL, CONF_TIMEOUT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from monarchmoney import MonarchMoney

from .const import DEFAULT_SCAN_INTERVAL, DEFAULT_TIMEOUT, DOMAIN, SESSION_FILE

PLATFORMS = ["sensor"]
_LOGGER = logging.getLogger(__name__)


class MonarchCoordinator(DataUpdateCoordinator):
    """Monarch Money data update coordinator."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self._hass = hass
        self._config_entry = config_entry
        self._api = MonarchMoney(session_file=self._hass.config.path(SESSION_FILE))
        # Session loading moved to async_setup to avoid blocking I/O in event loop

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
        )

    async def async_setup(self) -> bool:
        """Set up the coordinator."""
        _LOGGER.debug("Setting up coordinator")

        _LOGGER.debug("Loading session")
        # Load session in executor to avoid blocking I/O in event loop
        await self.hass.async_add_executor_job(
            self._api.load_session, self._hass.config.path(SESSION_FILE)
        )

        _LOGGER.debug("Getting first refresh")
        await self.async_config_entry_first_refresh()

        _LOGGER.debug("Forwarding setup to platforms")
        await self.hass.config_entries.async_forward_entry_setups(
            self._config_entry, PLATFORMS
        )

        return True

    async def async_reset(self) -> bool:
        """Reset the coordinator."""
        _LOGGER.debug("resetting the coordinator")
        entry = self._config_entry
        return all(
            await asyncio.gather(
                *[
                    self.hass.config_entries.async_forward_entry_unload(
                        entry, component
                    )
                    for component in PLATFORMS
                ]
            )
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            data = {"accounts": [], "categories": [], "cashflow": {}}

            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with asyncio.timeout(self._timeout):
                # Grab active context variables to limit data required to be fetched from API
                # Note: using context is not required if there is no need or ability to limit
                # data retrieved from API.
                try:
                    accounts = await self._api.get_accounts()
                    data["accounts"] = accounts.get("accounts") or []
                    _LOGGER.debug(f"Fetched {len(data['accounts'])} accounts from API")

                    categories = await self._api.get_transaction_categories()
                    data["categories"] = categories.get("categories") or []
                    _LOGGER.debug(
                        f"Fetched {len(data['categories'])} categories from API"
                    )

                    cashflow = await self._api.get_cashflow()
                    data["cashflow"] = cashflow or {}
                    _LOGGER.debug(f"Fetched cashflow data: {bool(data['cashflow'])}")

                    # Debug: log account types for troubleshooting
                    if data["accounts"]:
                        account_types = [
                            acc.get("type", {}).get("name")
                            for acc in data["accounts"]
                            if acc.get("type")
                        ]
                        _LOGGER.debug(f"Account types found: {set(account_types)}")

                except Exception as err:
                    _LOGGER.error(f"Error fetching data from Monarch API: {err}")
                    # Check if it's an authentication error
                    if (
                        "unauthorized" in str(err).lower()
                        or "authentication" in str(err).lower()
                    ):
                        raise ConfigEntryAuthFailed(
                            f"Authentication failed: {err}"
                        ) from err
                    raise UpdateFailed(f"Error communicating with API: {err}") from err
                return data
        except ConfigEntryAuthFailed as err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise ConfigEntryAuthFailed from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

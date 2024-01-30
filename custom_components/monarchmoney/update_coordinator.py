"""
Update coordinator
"""

import asyncio
from datetime import timedelta
import logging

import async_timeout

from homeassistant.const import (
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from monarchmoney import MonarchMoney
from .const import DEFAULT_SCAN_INTERVAL, DEFAULT_TIMEOUT, DOMAIN, SESSION_FILE

PLATFORMS = ["sensor"]
_LOGGER = logging.getLogger(__name__)


class MonarchCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass: HomeAssistant, config_entry) -> None:
        """Initialize my coordinator."""
        self._hass = hass
        self._config_entry = config_entry
        self._api = MonarchMoney(session_file=self._hass.config.path(SESSION_FILE))
        self._api.load_session(filename=self._hass.config.path(SESSION_FILE))

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

    async def async_setup(self):
        """Setup a new coordinator"""
        _LOGGER.debug("Setting up coordinator")

        _LOGGER.debug("Getting first refresh")
        await self.async_config_entry_first_refresh()

        _LOGGER.debug("Forwarding setup to platforms")
        for component in PLATFORMS:
            self.hass.async_create_task(
                self.hass.config_entries.async_forward_entry_setup(
                    self._config_entry, component
                )
            )

        return True

    async def async_reset(self):
        """Resets the coordinator."""
        _LOGGER.debug("resetting the coordinator")
        entry = self._config_entry
        unload_ok = all(
            await asyncio.gather(
                *[
                    self.hass.config_entries.async_forward_entry_unload(
                        entry, component
                    )
                    for component in PLATFORMS
                ]
            )
        )
        return unload_ok

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            data = {
                "accounts": {},
                "categories": {},
                "cashflow": {}
            }

            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            # TODO: configure timeout from config options
            async with async_timeout.timeout(10):
                # Grab active context variables to limit data required to be fetched from API
                # Note: using context is not required if there is no need or ability to limit
                # data retrieved from API.
                try:
                    accounts = await self._api.get_accounts()
                    data["accounts"] = accounts.get("accounts")
                    categories = await self._api.get_transaction_categories()
                    data["categories"] = categories.get("categories")
                    cashflow = await self._api.get_cashflow()
                    data["cashflow"] = cashflow
                except Exception as err:
                    raise err
                return data
        except ConfigEntryAuthFailed as err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise ConfigEntryAuthFailed from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

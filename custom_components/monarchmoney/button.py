"""Button platform for Monarch Money integration."""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .update_coordinator import MonarchCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Monarch Money buttons from a config entry."""
    coordinator: MonarchCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    unique_id = config_entry.unique_id
    async_add_entities(
        [MonarchRefreshButton(coordinator, unique_id)], True
    )


class MonarchRefreshButton(CoordinatorEntity, ButtonEntity):
    """Button to refresh Monarch Money accounts from institutions."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, unique_id) -> None:
        """Initialize the refresh button."""
        super().__init__(coordinator)
        self._attr_name = "Refresh Accounts"
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_refresh_accounts"
        self._attr_icon = "mdi:refresh"
        self._id = unique_id

    async def async_press(self) -> None:
        """Handle the button press."""
        accounts = self.coordinator.data.get("accounts", [])
        account_ids = [a["id"] for a in accounts if a.get("id")]
        if not account_ids:
            _LOGGER.warning("No accounts found to refresh")
            return

        _LOGGER.info("Requesting refresh for %d accounts", len(account_ids))
        try:
            await self.coordinator.api.request_accounts_refresh(account_ids)
        except Exception as err:
            _LOGGER.error("Failed to refresh accounts: %s", err)
            return

        await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._id)},
            name="Monarch",
            manufacturer="Monarch Money",
            model="Financial Account",
        )

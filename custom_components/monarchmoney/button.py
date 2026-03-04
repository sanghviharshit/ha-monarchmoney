"""Button platform for Monarch Money integration."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import MonarchEntity
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


class MonarchRefreshButton(MonarchEntity, ButtonEntity):
    """Button to refresh Monarch Money accounts from institutions."""

    def __init__(self, coordinator: MonarchCoordinator, unique_id: str) -> None:
        """Initialize the refresh button."""
        super().__init__(coordinator, unique_id)
        self._attr_name = "Refresh Accounts"
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_refresh_accounts"
        self._attr_icon = "mdi:refresh"

    async def async_press(self) -> None:
        """Handle the button press."""
        data = self.coordinator.data
        if not data:
            raise HomeAssistantError("No data available to refresh")

        account_ids = [a.id for a in data.accounts if a.id]
        if not account_ids:
            raise HomeAssistantError("No accounts found to refresh")

        _LOGGER.info("Requesting refresh for %d accounts", len(account_ids))
        try:
            await self.coordinator.api.request_accounts_refresh(account_ids)
        except Exception as err:
            raise HomeAssistantError(f"Failed to refresh accounts: {err}") from err

        await self.coordinator.async_request_refresh()

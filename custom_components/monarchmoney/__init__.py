"""The Monarch Money integration."""
from __future__ import annotations
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .update_coordinator import MonarchCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Monarch Money from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = MonarchCoordinator(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    if not await coordinator.async_setup():
        return False

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    coordinator: MonarchCoordinator = hass.data[DOMAIN][entry.entry_id]
    ok = await coordinator.async_reset()
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return ok


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry):
    """Update options."""
    await hass.config_entries.async_reload(config_entry.entry_id)

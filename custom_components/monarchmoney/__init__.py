"""The Monarch Money integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_ENABLE_AGGREGATED_HOLDINGS,
    CONF_ENABLE_CREDIT_SCORE,
    CONF_ENABLE_HOLDINGS,
    CONF_ENABLE_RECURRING,
    DOMAIN,
    PLATFORMS,
)
from .update_coordinator import MonarchCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Monarch Money from a config entry."""
    coordinator = MonarchCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_options))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return ok


async def _async_update_options(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Update options and clean up entities for disabled features."""
    _cleanup_disabled_entities(hass, config_entry)
    await hass.config_entries.async_reload(config_entry.entry_id)


def _cleanup_disabled_entities(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    """Remove entity registry entries for optional features that are now disabled."""
    ent_reg = er.async_get(hass)
    entries = er.async_entries_for_config_entry(ent_reg, config_entry.entry_id)
    options = config_entry.options
    uid = config_entry.unique_id
    prefix = f"{DOMAIN}_{uid}_"

    for entry in entries:
        should_remove = False

        # Calendar entities only come from recurring transactions
        if entry.domain == "calendar" and not options.get(
            CONF_ENABLE_RECURRING, False
        ):
            should_remove = True

        # Credit score sensors (per-user: credit_score_{user_id}, legacy: credit_score)
        elif (
            entry.domain == "sensor"
            and not options.get(CONF_ENABLE_CREDIT_SCORE, False)
            and (
                entry.unique_id == f"{prefix}credit_score"
                or entry.unique_id.startswith(f"{prefix}credit_score_")
            )
        ):
            should_remove = True

        # Aggregated holding sensors: unique_id contains "holding_agg_"
        elif (
            entry.domain == "sensor"
            and not options.get(CONF_ENABLE_AGGREGATED_HOLDINGS, False)
            and entry.unique_id.startswith(f"{prefix}holding_agg_")
        ):
            should_remove = True

        # Per-account holding sensors: unique_id contains "holding_acct_"
        elif (
            entry.domain == "sensor"
            and not options.get(CONF_ENABLE_HOLDINGS, False)
            and entry.unique_id.startswith(f"{prefix}holding_acct_")
        ):
            should_remove = True

        if should_remove:
            _LOGGER.debug(
                "Removing entity %s (feature disabled)", entry.entity_id
            )
            ent_reg.async_remove(entry.entity_id)



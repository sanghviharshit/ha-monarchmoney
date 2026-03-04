"""Base entity for Monarch Money integration."""

from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .update_coordinator import MonarchCoordinator


class MonarchEntity(CoordinatorEntity[MonarchCoordinator]):
    """Base entity for all Monarch Money entities."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: MonarchCoordinator, unique_id: str, **kwargs
    ) -> None:
        """Initialize with coordinator and config entry unique ID."""
        super().__init__(coordinator, **kwargs)
        self._id = unique_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info shared by all Monarch entities."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._id)},
            name="Monarch",
            manufacturer="Monarch Money",
            model="Financial Account",
        )

"""Category sensor for Monarch Money (one per account type)."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import callback

from ..const import DOMAIN
from ..update_coordinator import MonarchCoordinator
from ..util import format_date
from .base import MonarchSensorEntity
from .constants import CATEGORY_DISPLAY_OVERRIDE, GROUP_PREFIX, SENSOR_TYPES_GROUP

_LOGGER = logging.getLogger(__name__)


class MonarchMoneyCategorySensor(MonarchSensorEntity):
    """Monarch Money category sensor (sums balances per account type)."""

    def __init__(
        self, coordinator: MonarchCoordinator, category: str, unique_id: str
    ) -> None:
        """Initialize the category sensor."""
        super().__init__(coordinator, unique_id, context=category)
        self._account_type = SENSOR_TYPES_GROUP[category]["type"]
        group = SENSOR_TYPES_GROUP[category]["group"]
        prefix = GROUP_PREFIX[group]
        display_name = CATEGORY_DISPLAY_OVERRIDE.get(category, category)
        old_name = f"Monarch {category}"
        self._attr_name = f"{prefix} {display_name}"
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_{old_name.lower().replace(' ', '_')}"
        self._attr_icon = SENSOR_TYPES_GROUP[category]["icon"]
        self._account_data: dict[str, Any] = {}

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        if not data:
            return

        self._account_data = {}
        matching = [a for a in data.accounts if a.account_type.name == self._account_type]

        for account in matching:
            self._account_data[account.id] = {
                "id": account.id,
                "name": account.display_name,
                "balance": account.display_balance,
                "account_type": account.account_type.name,
                "updated": format_date(account.updated_at) if account.updated_at else "",
                "institution": account.institution.name if account.institution else None,
            }

        try:
            self._state = round(
                sum(a.display_balance for a in matching if a.display_balance is not None), 2
            )
        except (TypeError, ValueError) as err:
            _LOGGER.error("Error calculating sum for %s: %s", self._attr_name, err)
            self._state = 0

        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        if self.coordinator.data is not None:
            self._handle_coordinator_update()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        return self._account_data

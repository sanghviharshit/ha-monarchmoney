"""Net worth sensor for Monarch Money."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import callback

from ..update_coordinator import MonarchCoordinator
from ..const import DOMAIN
from .base import MonarchSensorEntity

_LOGGER = logging.getLogger(__name__)


class MonarchMoneyNetWorthSensor(MonarchSensorEntity):
    """Net worth sensor (assets minus liabilities for active accounts)."""

    def __init__(self, coordinator: MonarchCoordinator, unique_id: str) -> None:
        """Initialize the net worth sensor."""
        super().__init__(coordinator, unique_id)
        self._assets: float | None = None
        self._liabilities: float | None = None
        self._attr_name = "Summary Net Worth"
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_net_worth"
        self._attr_icon = "mdi:chart-donut"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        if not data:
            return

        # P0 BUG FIX: filter BOTH assets AND liabilities from active_accounts
        active_accounts = [
            a for a in data.accounts
            if a.include_in_net_worth and not a.is_hidden
        ]

        asset_accounts = [a for a in active_accounts if a.is_asset]
        liability_accounts = [a for a in active_accounts if not a.is_asset]

        asset_sum = round(
            sum(a.display_balance for a in asset_accounts if a.display_balance is not None), 2
        )
        liability_sum = round(
            sum(a.display_balance for a in liability_accounts if a.display_balance is not None), 2
        )

        self._state = asset_sum - liability_sum
        self._assets = asset_sum
        self._liabilities = liability_sum
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        return {"assets": self._assets, "liabilities": self._liabilities}

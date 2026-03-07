"""Summary sensors (total assets / total liabilities) for Monarch Money."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import callback

from ..const import DOMAIN
from ..update_coordinator import MonarchCoordinator
from .base import MonarchSensorEntity

_LOGGER = logging.getLogger(__name__)


class MonarchMoneyTotalAssetsSensor(MonarchSensorEntity):
    """Total assets sensor (sum of asset accounts included in net worth)."""

    def __init__(self, coordinator: MonarchCoordinator, unique_id: str) -> None:
        """Initialize the total assets sensor."""
        super().__init__(coordinator, unique_id)
        self._account_count: int = 0
        self._attr_name = "Summary Total Assets"
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_total_assets"
        self._attr_icon = "mdi:arrow-up-bold-circle"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        if not data:
            return

        asset_accounts = [
            a for a in data.accounts
            if a.is_asset and a.include_in_net_worth and not a.is_hidden
        ]

        self._state = round(
            sum(a.display_balance for a in asset_accounts if a.display_balance is not None), 2
        )
        self._account_count = len(asset_accounts)
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        return {"account_count": self._account_count}


class MonarchMoneyTotalLiabilitiesSensor(MonarchSensorEntity):
    """Total liabilities sensor (sum of liability accounts included in net worth)."""

    def __init__(self, coordinator: MonarchCoordinator, unique_id: str) -> None:
        """Initialize the total liabilities sensor."""
        super().__init__(coordinator, unique_id)
        self._account_count: int = 0
        self._attr_name = "Summary Total Liabilities"
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_total_liabilities"
        self._attr_icon = "mdi:arrow-down-bold-circle"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        if not data:
            return

        liability_accounts = [
            a for a in data.accounts
            if not a.is_asset and a.include_in_net_worth and not a.is_hidden
        ]

        self._state = round(
            sum(a.display_balance for a in liability_accounts if a.display_balance is not None), 2
        )
        self._account_count = len(liability_accounts)
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        return {"account_count": self._account_count}

"""Aggregated investment holding sensor for Monarch Money."""

from __future__ import annotations

from typing import Any

from homeassistant.core import callback

from ..const import DOMAIN
from ..update_coordinator import MonarchCoordinator
from .base import MonarchSensorEntity


class MonarchAggregatedHoldingSensor(MonarchSensorEntity):
    """Total value of a security aggregated across all brokerage accounts."""

    _attr_icon = "mdi:chart-areaspline"

    def __init__(
        self, coordinator: MonarchCoordinator, agg_data: dict[str, Any], unique_id: str
    ) -> None:
        """Initialize the aggregated holding sensor."""
        super().__init__(coordinator, unique_id)
        self._ticker: str = agg_data["ticker"]
        self._attr_name = f"Holding {self._ticker} Total"
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_holding_agg_{self._ticker}"
        self._attrs: dict[str, Any] = {}

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        if not data:
            return

        total_value = 0.0
        total_quantity = 0.0
        total_basis = 0.0
        accounts: list[str] = []
        current_price = None
        security_name = None
        security_type = None
        one_day_change_percent = None
        one_day_change_dollars = None

        for acct_holdings in data.holdings:
            for holding in acct_holdings.holdings:
                if holding.security.ticker == self._ticker:
                    total_value += holding.total_value or 0.0
                    total_quantity += holding.quantity or 0.0
                    total_basis += holding.basis or 0.0
                    accounts.append(acct_holdings.account.display_name)
                    current_price = holding.security.current_price
                    security_name = holding.security.name
                    security_type = holding.security.type_display
                    one_day_change_percent = holding.security.one_day_change_percent
                    one_day_change_dollars = holding.security.one_day_change_dollars

        self._state = round(total_value, 2)
        self._attrs = {
            "ticker": self._ticker,
            "security_name": security_name,
            "quantity": round(total_quantity, 4),
            "cost_basis": round(total_basis, 2),
            "current_price": current_price,
            "security_type": security_type,
            "one_day_change_percent": one_day_change_percent,
            "one_day_change_dollars": one_day_change_dollars,
            "accounts": accounts,
            "account_count": len(accounts),
        }
        if total_basis > 0:
            self._attrs["gain_loss"] = round(total_value - total_basis, 2)
            self._attrs["gain_loss_percent"] = round(
                ((total_value - total_basis) / total_basis) * 100, 2
            )

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        return self._attrs

"""Cash flow sensor for Monarch Money."""

from __future__ import annotations

from typing import Any

from homeassistant.core import callback

from ..const import DOMAIN
from ..update_coordinator import MonarchCoordinator
from .base import MonarchSensorEntity


class MonarchMoneyCashFlowSensor(MonarchSensorEntity):
    """Monthly savings (income minus expenses)."""

    def __init__(self, coordinator: MonarchCoordinator, unique_id: str) -> None:
        """Initialize the cash flow sensor."""
        super().__init__(coordinator, unique_id)
        self._income: float | None = None
        self._expenses: float | None = None
        self._savings: float | None = None
        self._savings_rate: float | None = None
        self._attr_name = "Cashflow Savings This Month"
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_cash_flow_this_month"
        self._attr_icon = "mdi:chart-sankey-variant"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        if not data or not data.cashflow or not data.cashflow.summary:
            return

        summary = data.cashflow.summary
        self._state = summary.savings
        self._income = summary.sum_income
        self._expenses = summary.sum_expense
        self._savings = summary.savings
        rate = summary.savings_rate
        self._savings_rate = rate * 100 if rate is not None else None

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        return {
            "income": self._income,
            "expense": self._expenses,
            "savings": self._savings,
            "savings_rate": self._savings_rate,
        }

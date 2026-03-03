"""Expense sensor for Monarch Money."""

from __future__ import annotations

from typing import Any

from homeassistant.core import callback

from ..const import DOMAIN
from ..update_coordinator import MonarchCoordinator
from .base import MonarchSensorEntity


class MonarchMoneyExpenseSensor(MonarchSensorEntity):
    """Monthly expense total with per-category breakdown."""

    def __init__(self, coordinator: MonarchCoordinator, unique_id: str) -> None:
        """Initialize the expense sensor."""
        super().__init__(coordinator, unique_id)
        self._attr_name = "Cashflow Expenses This Month"
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_expenses_this_month"
        self._attr_icon = "mdi:bank-minus"
        self._expense_cats: dict[str, float] = {}

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        if not data:
            return

        # Build category map from categories list
        expense_cats: dict[str, float] = {}
        for cat in data.categories:
            if cat.group and cat.group.type == "expense":
                expense_cats[cat.name] = 0.0

        # Fill from cashflow by-category data (negate values)
        for by_cat in data.cashflow.by_category:
            if by_cat.category_group_type == "expense" and by_cat.category_name in expense_cats:
                expense_cats[by_cat.category_name] += -1 * by_cat.total

        sum_expense = data.cashflow.summary.sum_expense if data.cashflow.summary else None
        self._state = -1 * sum_expense if sum_expense is not None else None
        self._expense_cats = expense_cats
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        return {"categories": self._expense_cats}

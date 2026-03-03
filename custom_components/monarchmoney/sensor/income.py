"""Income sensor for Monarch Money."""

from __future__ import annotations

from typing import Any

from homeassistant.core import callback

from ..const import DOMAIN
from ..update_coordinator import MonarchCoordinator
from .base import MonarchSensorEntity


class MonarchMoneyIncomeSensor(MonarchSensorEntity):
    """Monthly income total with per-category breakdown."""

    def __init__(self, coordinator: MonarchCoordinator, unique_id: str) -> None:
        """Initialize the income sensor."""
        super().__init__(coordinator, unique_id)
        self._attr_name = "Cashflow Income This Month"
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_income_this_month"
        self._attr_icon = "mdi:bank-plus"
        self._income_cats: dict[str, float] = {}

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        if not data or not data.cashflow:
            return

        # Build category map from categories list
        income_cats: dict[str, float] = {}
        for cat in data.categories:
            if cat.group is not None and cat.group.type == "income":
                income_cats[cat.name] = 0.0

        # Fill from cashflow by-category data
        for by_cat in data.cashflow.by_category:
            if by_cat.category_group_type == "income" and by_cat.category_name in income_cats:
                income_cats[by_cat.category_name] += by_cat.total

        self._state = data.cashflow.summary.sum_income if data.cashflow.summary else None
        self._income_cats = income_cats
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        return {"categories": self._income_cats}

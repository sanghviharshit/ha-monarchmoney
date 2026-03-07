"""Per-account investment holding sensor for Monarch Money."""

from __future__ import annotations

from typing import Any

from homeassistant.core import callback

from ..const import DOMAIN
from ..models import Account, Holding
from ..update_coordinator import MonarchCoordinator
from .base import MonarchSensorEntity


class MonarchHoldingSensor(MonarchSensorEntity):
    """Individual security holding within a brokerage account."""

    def __init__(
        self,
        coordinator: MonarchCoordinator,
        holding: Holding,
        account: Account,
        unique_id: str,
    ) -> None:
        """Initialize the holding sensor."""
        super().__init__(coordinator, unique_id)
        self._holding_id = holding.id
        self._account_id = account.id
        self._account_name = account.display_name
        self._ticker = holding.security.ticker
        security_name = holding.security.name or self._ticker

        self._attr_name = f"Holding {self._ticker or security_name} ({self._account_name})"
        self._attr_unique_id = (
            f"{DOMAIN}_{unique_id}_holding_acct_{self._account_id}_{self._holding_id}"
        )
        self._attr_icon = "mdi:chart-line"
        self._attrs: dict[str, Any] = {}

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        if not data:
            return

        for acct_holdings in data.holdings:
            if acct_holdings.account.id != self._account_id:
                continue
            for holding in acct_holdings.holdings:
                if holding.id != self._holding_id:
                    continue
                self._state = holding.total_value
                sec = holding.security
                self._attrs = {
                    "ticker": sec.ticker,
                    "security_name": sec.name,
                    "quantity": holding.quantity,
                    "cost_basis": holding.basis,
                    "current_price": sec.current_price,
                    "security_type": sec.type_display,
                    "one_day_change_percent": sec.one_day_change_percent,
                    "one_day_change_dollars": sec.one_day_change_dollars,
                    "account_name": self._account_name,
                }
                if holding.basis is not None and holding.total_value is not None:
                    self._attrs["gain_loss"] = round(holding.total_value - holding.basis, 2)
                    if holding.basis > 0:
                        self._attrs["gain_loss_percent"] = round(
                            ((holding.total_value - holding.basis) / holding.basis) * 100, 2
                        )
                break
            break

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        return self._attrs

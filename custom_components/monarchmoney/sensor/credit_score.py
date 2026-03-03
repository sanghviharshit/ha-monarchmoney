"""Credit score sensor for Monarch Money."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor.const import SensorStateClass
from homeassistant.core import callback

from ..const import DOMAIN
from ..entity import MonarchEntity
from ..update_coordinator import MonarchCoordinator

from homeassistant.components.sensor import SensorEntity


class MonarchCreditScoreSensor(MonarchEntity, SensorEntity):
    """Credit score sensor for a specific household member."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: MonarchCoordinator,
        unique_id: str,
        user_id: str,
        user_name: str,
    ) -> None:
        """Initialize the credit score sensor."""
        super().__init__(coordinator, unique_id)
        self._user_id = user_id
        self._user_name = user_name
        self._state: int | None = None
        self._reported_date: str | None = None
        self._previous_score: int | None = None
        self._score_change: int | None = None
        self._attr_name = f"Credit Score ({user_name})"
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_credit_score_{user_id}"
        self._attr_icon = "mdi:credit-card-check"

    @property
    def native_value(self) -> int | None:
        """Return the native value of the sensor."""
        return self._state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        if not data or not data.credit_history:
            return

        # Filter snapshots for this user
        snapshots = [
            s for s in data.credit_history.snapshots
            if s.user_id == self._user_id
        ]
        if not snapshots:
            return

        sorted_snaps = sorted(snapshots, key=lambda s: s.reported_date or "")
        latest = sorted_snaps[-1]
        self._state = latest.score
        self._reported_date = latest.reported_date

        if len(sorted_snaps) >= 2:
            previous = sorted_snaps[-2]
            self._previous_score = previous.score
            if self._state is not None and self._previous_score is not None:
                self._score_change = self._state - self._previous_score
        else:
            self._previous_score = None
            self._score_change = None

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        return {
            "user_name": self._user_name,
            "reported_date": self._reported_date,
            "previous_score": self._previous_score,
            "score_change": self._score_change,
        }

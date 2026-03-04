"""Calendar platform for Monarch Money recurring transactions."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import logging

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ENABLE_RECURRING, DOMAIN
from .entity import MonarchEntity
from .update_coordinator import MonarchCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Monarch Money calendar from a config entry."""
    if not config_entry.options.get(CONF_ENABLE_RECURRING, False):
        return

    coordinator: MonarchCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    unique_id = config_entry.unique_id
    async_add_entities(
        [MonarchRecurringCalendar(coordinator, unique_id)], True
    )


class MonarchRecurringCalendar(MonarchEntity, CalendarEntity):
    """Calendar entity for Monarch Money recurring transactions."""

    def __init__(self, coordinator: MonarchCoordinator, unique_id: str) -> None:
        """Initialize the recurring transactions calendar."""
        super().__init__(coordinator, unique_id)
        self._attr_name = "Recurring Transactions"
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_recurring_calendar"
        self._events: list[CalendarEvent] = []

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        today = date.today()
        upcoming = [
            e for e in self._events if e.start >= today
        ]
        if upcoming:
            upcoming.sort(key=lambda e: e.start)
            return upcoming[0]
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return events in a specific date range."""
        s = start_date.date() if isinstance(start_date, datetime) else start_date
        e = end_date.date() if isinstance(end_date, datetime) else end_date
        return [
            ev for ev in self._events if s <= ev.start <= e
        ]

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        if not data:
            return

        events: list[CalendarEvent] = []
        for item in data.recurring:
            try:
                item_date = date.fromisoformat(item.date)
            except (ValueError, TypeError):
                continue

            amount_str = f"${abs(item.amount):.2f}" if item.amount is not None else ""
            summary = f"{item.merchant_name} {amount_str}".strip()

            description_parts: list[str] = []
            if item.category_name:
                description_parts.append(f"Category: {item.category_name}")
            if item.account_name:
                description_parts.append(f"Account: {item.account_name}")
            if item.frequency:
                description_parts.append(f"Frequency: {item.frequency}")

            events.append(
                CalendarEvent(
                    start=item_date,
                    end=item_date + timedelta(days=1),
                    summary=summary,
                    description="\n".join(description_parts),
                )
            )

        self._events = events
        self.async_write_ha_state()

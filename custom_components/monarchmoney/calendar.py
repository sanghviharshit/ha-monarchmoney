"""Calendar platform for Monarch Money recurring transactions."""

from datetime import date, datetime, timedelta
import logging

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ENABLE_RECURRING, DOMAIN
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


class MonarchRecurringCalendar(CoordinatorEntity, CalendarEntity):
    """Calendar entity for Monarch Money recurring transactions."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, unique_id) -> None:
        """Initialize the recurring transactions calendar."""
        super().__init__(coordinator)
        self._attr_name = "Recurring Transactions"
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_recurring_calendar"
        self._id = unique_id
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
        update_data = self.coordinator.data
        if not update_data:
            return

        recurring_data = update_data.get("recurring", {})
        items = recurring_data.get("recurringTransactionItems") or []

        events: list[CalendarEvent] = []
        for item in items:
            item_date_str = item.get("date")
            if not item_date_str:
                continue

            try:
                item_date = date.fromisoformat(item_date_str)
            except (ValueError, TypeError):
                continue

            stream = item.get("stream") or {}
            merchant = stream.get("merchant") or {}
            merchant_name = merchant.get("name", "Unknown")
            amount = item.get("amount")
            amount_str = f"${abs(amount):.2f}" if amount is not None else ""
            category = item.get("category") or {}
            category_name = category.get("name", "")
            account = item.get("account") or {}
            account_name = account.get("displayName", "")
            frequency = stream.get("frequency", "")

            summary = f"{merchant_name} {amount_str}".strip()
            description_parts = []
            if category_name:
                description_parts.append(f"Category: {category_name}")
            if account_name:
                description_parts.append(f"Account: {account_name}")
            if frequency:
                description_parts.append(f"Frequency: {frequency}")

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

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._id)},
            name="Monarch",
            manufacturer="Monarch Money",
            model="Financial Account",
        )

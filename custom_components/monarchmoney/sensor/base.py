"""Base sensor entity for Monarch Money."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass

from ..entity import MonarchEntity
from ..update_coordinator import MonarchCoordinator


class MonarchSensorEntity(MonarchEntity, SensorEntity):
    """Base for monetary sensor entities."""

    _attr_native_unit_of_measurement = "USD"
    # TODO: Read currency from Monarch API instead of hardcoding USD
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, coordinator: MonarchCoordinator, unique_id: str, **kwargs) -> None:
        """Initialize the sensor entity."""
        super().__init__(coordinator, unique_id, **kwargs)
        self._state: float | int | None = None

    @property
    def native_value(self) -> float | int | None:
        """Return the native value of the sensor."""
        return self._state

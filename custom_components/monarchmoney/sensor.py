"""Sensor Platform"""
import logging
from .util import format_date

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity


from .const import DOMAIN

from .update_coordinator import MonarchCoordinator

_LOGGER = logging.getLogger(__name__)

ATTR_ASSETS = "ASSETS"
ATTR_LIABILITIES = "LIABILITIES"

ATTR_BROKERAGE = "Investments"
ATTR_CREDIT = "Credit Cards"
ATTR_DEPOSITORY = "Cash"
ATTR_LOAN = "Loans"
ATTR_OTHER = "Other"
ATTR_REAL_ESTATE = "Real Estate"
ATTR_VALUABLE = "Valuables"
ATTR_VEHICLE = "Vehicles"
ATTR_OTHER_ASSET = "Other Assets"
ATTR_OTHER_LIABILITY = "Other Liabilities"

SENSOR_TYPES_GROUP = {
    ATTR_BROKERAGE: {
        "type": "brokerage",
        "group": ATTR_ASSETS,
        "icon": "mdi:chart-line",
    },
    ATTR_CREDIT: {
        "type": "credit",
        "group": ATTR_LIABILITIES,
        "icon": "mdi:credit-card",
    },
    ATTR_DEPOSITORY: {"type": "depository", "group": ATTR_ASSETS, "icon": "mdi:cash"},
    ATTR_LOAN: {"type": "loan", "group": ATTR_LIABILITIES, "icon": "mdi:bank"},
    ATTR_OTHER: {"type": "other", "group": "OTHER", "icon": "mdi:information-outline"},
    ATTR_REAL_ESTATE: {"type": "real_estate", "group": ATTR_ASSETS, "icon": "mdi:home"},
    ATTR_VALUABLE: {
        "type": "valuables",
        "group": ATTR_ASSETS,
        "icon": "mdi:treasure-chest",
    },
    ATTR_VEHICLE: {"type": "vehicle", "group": ATTR_ASSETS, "icon": "mdi:car"},
    ATTR_OTHER_ASSET: {
        "type": "other_asset",
        "group": ATTR_ASSETS,
        "icon": "mdi:file-document-outline",
    },
    ATTR_OTHER_LIABILITY: {
        "type": "other_liability",
        "group": ATTR_LIABILITIES,
        "icon": "mdi:account-alert-outline",
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Config entry example."""

    coordinator: MonarchCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    unique_id = config_entry.unique_id
    categories = SENSOR_TYPES_GROUP.keys()
    sensors = []
    for category in categories:
        sensors.append(MonarchMoneyCategorySensor(coordinator, category, unique_id))

    sensors.append(MonarchMoneyNetWorthSensor(coordinator, unique_id))
    sensors.append(MonarchMoneyCashFlowSensor(coordinator, unique_id))
    sensors.append(MonarchMoneyIncomeSensor(coordinator, unique_id))
    sensors.append(MonarchMoneyExpenseSensor(coordinator, unique_id))

    async_add_entities(sensors, True)


class MonarchMoneyCategorySensor(CoordinatorEntity, SensorEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available

    """

    def __init__(self, coordinator, category, unique_id) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context=category)
        self._account_type = SENSOR_TYPES_GROUP[category]["type"]
        # self._account_group = SENSOR_TYPES_GROUP[category]["group"]
        self._name = f"Monarch { category }"
        self._state = None
        self._account_data = {}
        self._id = unique_id
        self._attr_icon = SENSOR_TYPES_GROUP[category]["icon"]
        self._attr_native_unit_of_measurement = "USD"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def unique_id(self) -> str:
        return self._name.lower()

    @property
    def native_value(self):
        return self._state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        update_data = self.coordinator.data

        accounts = update_data.get("accounts")

        self._account_data = {}

        sensor_type_accounts = [
            account
            for account in accounts
            if account.get("type").get("name") == self._account_type
        ]

        for account in sensor_type_accounts:
            institution = None
            try:
                institution = (
                    account.get("credential").get("institution").get("name", "")
                )
            except AttributeError:
                pass

            self._account_data[account.get("id", "")] = {
                "id": account.get("id", ""),
                "name": account.get("displayName", ""),
                "balance": account.get("displayBalance", ""),
                "account_type": account.get("type").get("name", ""),
                "updated": format_date(account.get("updatedAt", "")),
                "institution": institution,
            }

        sensor_type_accounts_sum = round(
            sum(
                sensor_type_account["displayBalance"]
                for sensor_type_account in sensor_type_accounts
            )
        )

        self._state = sensor_type_accounts_sum

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return self._account_data

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._id)
            },
            name=self._id,
            manufacturer=DOMAIN,
            via_device=(DOMAIN, self._id),
        )


class MonarchMoneyNetWorthSensor(CoordinatorEntity, SensorEntity):
    """Representation of a monarchmoney.com net worth sensor."""

    def __init__(self, coordinator, unique_id) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._state = None
        self._assets = None
        self._liabilities = None
        self._name = "Monarch Net Worth"
        self._id = unique_id
        self._attr_native_unit_of_measurement = "USD"
        self._attr_icon = "mdi:chart-donut"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def unique_id(self) -> str:
        return self._name.lower()

    @property
    def native_value(self):
        return self._state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        update_data = self.coordinator.data
        accounts = update_data.get("accounts")
        active_accounts = [
            account for account in accounts if account["includeInNetWorth"] is True and account["isHidden"] is False
        ]

        asset_accounts = [
            account
            for account in active_accounts
            if account["isAsset"] is True
            # and account["type"]["name"] in ASSET_ACCOUNT_TYPES
        ]
        liability_accounts = [
            account
            for account in accounts
            if account["isAsset"] is False
            # and account["type"]["name"] in LIABILITY_ACCOUNT_TYPES
        ]

        asset_accounts_sum = round(
            sum(asset_account["displayBalance"] for asset_account in asset_accounts)
        )
        liability_accounts_sum = round(
            sum(
                liability_account["displayBalance"]
                for liability_account in liability_accounts
            )
        )

        active_accounts_sum = asset_accounts_sum - liability_accounts_sum

        self._state = active_accounts_sum
        self._assets = asset_accounts_sum
        self._liabilities = liability_accounts_sum
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        attributes = {"assets": self._assets, "liabilities": self._liabilities}
        return attributes

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._id)
            },
            name=self._id,
            manufacturer=DOMAIN,
            via_device=(DOMAIN, self._id),
        )


class MonarchMoneyCashFlowSensor(CoordinatorEntity, SensorEntity):
    """Representation of a monarchmoney.com cash flow sensor."""

    def __init__(self, coordinator, unique_id) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._state = None
        self._income = None
        self._expenses = None
        self._savings = None
        self._savings_rate = None
        self._name = "Monarch Cash Flow"
        self._id = unique_id
        self._attr_native_unit_of_measurement = "USD"
        self._attr_icon = "mdi:chart-sankey-variant"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def unique_id(self) -> str:
        return self._name.lower()

    @property
    def native_value(self):
        return self._state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        update_data = self.coordinator.data
        cashflow = update_data.get("cashflow")

        c = cashflow.get("summary")[0]

        self._state = c.get("summary").get("savings")
        self._income = c.get("summary").get("sumIncome")
        self._expenses = c.get("summary").get("sumExpense")
        self._savings = c.get("summary").get("savings")
        self._savings_rate = c.get("summary").get("savingsRate") * 100

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        attributes = {
            "income": self._income,
            "expense": self._expenses,
            "savings": self._savings,
            "savings_rate": self._savings_rate,
        }
        return attributes

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._id)
            },
            name=self._id,
            manufacturer=DOMAIN,
            via_device=(DOMAIN, self._id),
        )


class MonarchMoneyIncomeSensor(CoordinatorEntity, SensorEntity):
    """Representation of a monarchmoney.com income sensor."""

    def __init__(self, coordinator, unique_id) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._state = None
        self._income = None
        self._name = "Monarch Income"
        self._id = unique_id
        self._attr_native_unit_of_measurement = "USD"
        self._attr_icon = "mdi:bank-plus"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL
        self._income_cats = {}

    @property
    def unique_id(self) -> str:
        return self._name.lower()

    @property
    def native_value(self):
        return self._state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        update_data = self.coordinator.data

        income_cats = dict()
        for c in update_data.get("categories"):
            if c.get("group").get("type") == "income":
                income_cats[c.get("name")] = 0.0

        cashflow = update_data.get("cashflow")
        for c in cashflow.get("byCategory"):
            if c.get("groupBy").get("category").get("group").get("type") == "income":
                income_cats[c.get("groupBy").get("category").get("name")] += c.get(
                    "summary"
                ).get("sum")

        c = cashflow.get("summary")[0]

        self._state = c.get("summary").get("sumIncome")
        self._income_cats = income_cats

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        attributes = {"categories": self._income_cats}
        return attributes

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._id)
            },
            name=self._id,
            manufacturer=DOMAIN,
            via_device=(DOMAIN, self._id),
        )


class MonarchMoneyExpenseSensor(CoordinatorEntity, SensorEntity):
    """Representation of a monarchmoney.com expense sensor."""

    def __init__(self, coordinator, unique_id) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._state = None
        self._income = None
        self._name = "Monarch Expense"
        self._id = unique_id
        self._attr_native_unit_of_measurement = "USD"
        self._attr_icon = "mdi:bank-minus"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL
        self._expense_cats = {}

    @property
    def unique_id(self) -> str:
        return self._name.lower()

    @property
    def native_value(self):
        return self._state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        update_data = self.coordinator.data

        expense_cats = dict()
        for c in update_data.get("categories"):
            if c.get("group").get("type") == "expense":
                expense_cats[c.get("name")] = 0.0

        cashflow = update_data.get("cashflow")
        for c in cashflow.get("byCategory"):
            if c.get("groupBy").get("category").get("group").get("type") == "expense":
                expense_cats[c.get("groupBy").get("category").get("name")] += -1 * c.get(
                    "summary"
                ).get("sum")


        c = cashflow.get("summary")[0]

        self._state = -1 * c.get("summary").get("sumExpense")
        self._expense_cats = expense_cats

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        attributes = {"categories": self._expense_cats}
        return attributes

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._id)
            },
            name=self._id,
            manufacturer=DOMAIN,
            via_device=(DOMAIN, self._id),
        )

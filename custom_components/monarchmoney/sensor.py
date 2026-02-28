"""Sensor platform for Monarch Money integration."""

import contextlib
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .update_coordinator import MonarchCoordinator
from .util import format_date

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
    """Set up Monarch Money sensors from a config entry."""

    coordinator: MonarchCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    unique_id = config_entry.unique_id
    categories = SENSOR_TYPES_GROUP.keys()
    sensors: list[SensorEntity] = [
        MonarchMoneyCategorySensor(coordinator, category, unique_id)
        for category in categories
    ]
    sensors.append(MonarchMoneyNetWorthSensor(coordinator, unique_id))
    sensors.append(MonarchMoneyCashFlowSensor(coordinator, unique_id))
    sensors.append(MonarchMoneyIncomeSensor(coordinator, unique_id))
    sensors.append(MonarchMoneyExpenseSensor(coordinator, unique_id))

    async_add_entities(sensors, True)


class MonarchMoneyCategorySensor(CoordinatorEntity, SensorEntity):
    """Monarch Money category sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, category, unique_id) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context=category)
        self._account_type = SENSOR_TYPES_GROUP[category]["type"]
        # self._account_group = SENSOR_TYPES_GROUP[category]["group"]
        self._attr_name = category
        old_name = f"Monarch {category}"
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_{old_name.lower().replace(' ', '_')}"
        self._state = None  # Keep None for initial state to show "Unknown"
        self._account_data = {}
        self._id = unique_id
        self._attr_icon = SENSOR_TYPES_GROUP[category]["icon"]
        self._attr_native_unit_of_measurement = "USD"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        return self._state

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        # Ensure we get an initial update if coordinator already has data
        if self.coordinator.data is not None:
            _LOGGER.debug("Forcing initial update for %s", self._attr_name)
            self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        update_data = self.coordinator.data

        if not update_data:
            _LOGGER.warning("No data available for %s", self._attr_name)
            return

        _LOGGER.debug("Updating sensor: %s", self._attr_name)
        _LOGGER.debug("Looking for account type: %s", self._account_type)
        _LOGGER.debug(
            "Coordinator data keys: %s",
            list(update_data.keys()) if update_data else "None",
        )

        accounts = update_data.get("accounts", [])

        _LOGGER.debug(
            "Total accounts found: %s",
            len(accounts) if isinstance(accounts, list) else "Not a list",
        )

        self._account_data = {}

        sensor_type_accounts = [
            account
            for account in accounts
            if account.get("type", {}).get("name") == self._account_type
        ]

        _LOGGER.debug(
            "Matching accounts for %s: %d", self._account_type, len(sensor_type_accounts)
        )

        if not sensor_type_accounts:
            _LOGGER.debug(
                "No accounts found for type '%s' in %s", self._account_type, self._attr_name
            )
            # Log available account types for debugging
            available_types = [
                account.get("type", {}).get("name")
                for account in accounts
                if account.get("type")
            ]
            _LOGGER.debug("Available account types: %s", set(available_types))

        for account in sensor_type_accounts:
            institution = None
            with contextlib.suppress(AttributeError):
                institution = (
                    account.get("credential", {}).get("institution", {}).get("name", "")
                )

            self._account_data[account.get("id", "")] = {
                "id": account.get("id", ""),
                "name": account.get("displayName", ""),
                "balance": account.get("displayBalance", ""),
                "account_type": account.get("type", {}).get("name", ""),
                "updated": format_date(account.get("updatedAt", "")),
                "institution": institution,
            }

        try:
            sensor_type_accounts_sum = round(
                sum(
                    sensor_type_account["displayBalance"]
                    for sensor_type_account in sensor_type_accounts
                    if sensor_type_account.get("displayBalance") is not None
                ),
                2,
            )
            _LOGGER.debug(
                "Calculated sum for %s: %s", self._attr_name, sensor_type_accounts_sum
            )
        except (TypeError, ValueError) as err:
            _LOGGER.error("Error calculating sum for %s: %s", self._attr_name, err)
            sensor_type_accounts_sum = 0

        self._state = sensor_type_accounts_sum

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return self._account_data

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._id)},
            name="Monarch Money",
            manufacturer="Monarch Money",
            model="Financial Account",
        )


class MonarchMoneyNetWorthSensor(CoordinatorEntity, SensorEntity):
    """Representation of a monarchmoney.com net worth sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, unique_id) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._state = None
        self._assets = None
        self._liabilities = None
        self._attr_name = "Net Worth"
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_net_worth"
        self._id = unique_id
        self._attr_native_unit_of_measurement = "USD"
        self._attr_icon = "mdi:chart-donut"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        return self._state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        update_data = self.coordinator.data

        if not update_data:
            _LOGGER.warning("No data available for %s", self._attr_name)
            return

        accounts = update_data.get("accounts", [])
        active_accounts = [
            account
            for account in accounts
            if account.get("includeInNetWorth") is True
            and account.get("isHidden") is False
        ]

        asset_accounts = [
            account
            for account in active_accounts
            if account.get("isAsset") is True
        ]
        liability_accounts = [
            account
            for account in accounts
            if account.get("isAsset") is False
        ]

        asset_accounts_sum = round(
            sum(
                a.get("displayBalance", 0)
                for a in asset_accounts
                if a.get("displayBalance") is not None
            ),
            2,
        )
        liability_accounts_sum = round(
            sum(
                a.get("displayBalance", 0)
                for a in liability_accounts
                if a.get("displayBalance") is not None
            ),
            2,
        )

        active_accounts_sum = asset_accounts_sum - liability_accounts_sum

        self._state = active_accounts_sum
        self._assets = asset_accounts_sum
        self._liabilities = liability_accounts_sum
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {"assets": self._assets, "liabilities": self._liabilities}

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._id)},
            name="Monarch Money",
            manufacturer="Monarch Money",
            model="Financial Account",
        )


class MonarchMoneyCashFlowSensor(CoordinatorEntity, SensorEntity):
    """Representation of a monarchmoney.com cash flow sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, unique_id) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._state = None
        self._income = None
        self._expenses = None
        self._savings = None
        self._savings_rate = None
        self._attr_name = "Cash Flow"
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_cash_flow"
        self._id = unique_id
        self._attr_native_unit_of_measurement = "USD"
        self._attr_icon = "mdi:chart-sankey-variant"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        return self._state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        update_data = self.coordinator.data

        if not update_data:
            _LOGGER.warning("No data available for %s", self._attr_name)
            return

        cashflow = update_data.get("cashflow", {})

        summary_list = cashflow.get("summary") or []
        if not summary_list:
            return

        c = summary_list[0]
        summary = c.get("summary") or {}

        self._state = summary.get("savings")
        self._income = summary.get("sumIncome")
        self._expenses = summary.get("sumExpense")
        self._savings = summary.get("savings")
        savings_rate = summary.get("savingsRate")
        self._savings_rate = savings_rate * 100 if savings_rate is not None else None

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            "income": self._income,
            "expense": self._expenses,
            "savings": self._savings,
            "savings_rate": self._savings_rate,
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._id)},
            name="Monarch Money",
            manufacturer="Monarch Money",
            model="Financial Account",
        )


class MonarchMoneyIncomeSensor(CoordinatorEntity, SensorEntity):
    """Representation of a monarchmoney.com income sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, unique_id) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._state = None
        self._income = None
        self._attr_name = "Income"
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_income"
        self._id = unique_id
        self._attr_native_unit_of_measurement = "USD"
        self._attr_icon = "mdi:bank-plus"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL
        self._income_cats = {}

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        return self._state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        update_data = self.coordinator.data

        income_cats = {}
        for c in update_data.get("categories", []):
            group = c.get("group") or {}
            if group.get("type") == "income":
                income_cats[c.get("name")] = 0.0

        cashflow = update_data.get("cashflow", {})
        for c in cashflow.get("byCategory", []):
            group_by = c.get("groupBy") or {}
            category = group_by.get("category") or {}
            group = category.get("group") or {}
            if group.get("type") == "income":
                cat_name = category.get("name")
                cat_summary = c.get("summary") or {}
                if cat_name in income_cats:
                    income_cats[cat_name] += cat_summary.get("sum", 0)

        summary_list = cashflow.get("summary") or [{}]
        c = summary_list[0]
        summary = c.get("summary") or {}

        self._state = summary.get("sumIncome")
        self._income_cats = income_cats

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {"categories": self._income_cats}

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._id)},
            name="Monarch Money",
            manufacturer="Monarch Money",
            model="Financial Account",
        )


class MonarchMoneyExpenseSensor(CoordinatorEntity, SensorEntity):
    """Representation of a monarchmoney.com expense sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, unique_id) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._state = None
        self._income = None
        self._attr_name = "Expenses"
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_expense"
        self._id = unique_id
        self._attr_native_unit_of_measurement = "USD"
        self._attr_icon = "mdi:bank-minus"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL
        self._expense_cats = {}

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        return self._state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        update_data = self.coordinator.data

        expense_cats = {}
        for c in update_data.get("categories", []):
            group = c.get("group") or {}
            if group.get("type") == "expense":
                expense_cats[c.get("name")] = 0.0

        cashflow = update_data.get("cashflow", {})
        for c in cashflow.get("byCategory", []):
            group_by = c.get("groupBy") or {}
            category = group_by.get("category") or {}
            group = category.get("group") or {}
            if group.get("type") == "expense":
                cat_name = category.get("name")
                cat_summary = c.get("summary") or {}
                if cat_name in expense_cats:
                    expense_cats[cat_name] += -1 * cat_summary.get("sum", 0)

        summary_list = cashflow.get("summary") or [{}]
        c = summary_list[0]
        summary = c.get("summary") or {}

        sum_expense = summary.get("sumExpense")
        self._state = -1 * sum_expense if sum_expense is not None else None
        self._expense_cats = expense_cats

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {"categories": self._expense_cats}

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._id)},
            name="Monarch Money",
            manufacturer="Monarch Money",
            model="Financial Account",
        )

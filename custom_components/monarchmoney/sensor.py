"""Sensor platform for Monarch Money integration."""

import contextlib
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_ENABLE_AGGREGATED_HOLDINGS,
    CONF_ENABLE_CREDIT_SCORE,
    CONF_ENABLE_HOLDINGS,
    DOMAIN,
)
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

# Prefix for entity names based on account group
GROUP_PREFIX = {
    ATTR_ASSETS: "Assets",
    ATTR_LIABILITIES: "Liabilities",
    "OTHER": "Accounts",
}

# Override display name for categories where the raw name is redundant with the prefix
CATEGORY_DISPLAY_OVERRIDE = {
    ATTR_OTHER_ASSET: "Other",
    ATTR_OTHER_LIABILITY: "Other",
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Monarch Money sensors from a config entry."""

    coordinator: MonarchCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    unique_id = config_entry.unique_id
    options = config_entry.options

    # Check which account types actually have data for conditional sensors
    accounts = coordinator.data.get("accounts", []) if coordinator.data else []
    account_types_present = {
        a.get("type", {}).get("name") for a in accounts if a.get("type")
    }

    sensors: list[SensorEntity] = []
    for category in SENSOR_TYPES_GROUP:
        # Only create "Other" sensor if accounts of that type exist
        if category == ATTR_OTHER and "other" not in account_types_present:
            continue
        sensors.append(
            MonarchMoneyCategorySensor(coordinator, category, unique_id)
        )
    sensors.append(MonarchMoneyNetWorthSensor(coordinator, unique_id))
    sensors.append(MonarchMoneyCashFlowSensor(coordinator, unique_id))
    sensors.append(MonarchMoneyIncomeSensor(coordinator, unique_id))
    sensors.append(MonarchMoneyExpenseSensor(coordinator, unique_id))

    # Migrate: remove legacy cashflow entities renamed to *_this_month
    ent_reg = er.async_get(hass)
    legacy_cashflow_ids = [
        f"{DOMAIN}_{unique_id}_cash_flow",
        f"{DOMAIN}_{unique_id}_income",
        f"{DOMAIN}_{unique_id}_expense",
    ]
    for legacy_uid in legacy_cashflow_ids:
        old_eid = ent_reg.async_get_entity_id("sensor", DOMAIN, legacy_uid)
        if old_eid:
            _LOGGER.debug("Removing legacy cashflow entity %s", old_eid)
            ent_reg.async_remove(old_eid)

    if options.get(CONF_ENABLE_CREDIT_SCORE, False):
        credit_data = coordinator.data.get("credit_history", {})
        snapshots = credit_data.get("creditScoreSnapshots") or []
        household = credit_data.get("myHousehold", {})
        household_users = household.get("users", [])
        user_names = {
            u["id"]: u.get("displayName") or u.get("name", "Unknown")
            for u in household_users
            if u.get("id")
        }

        # Find users that have credit score data
        user_ids_with_scores = {
            snap["user"]["id"]
            for snap in snapshots
            if snap.get("user", {}).get("id")
        }

        for user_id in user_ids_with_scores:
            display_name = user_names.get(user_id, "Unknown")
            sensors.append(
                MonarchCreditScoreSensor(
                    coordinator, unique_id, user_id, display_name
                )
            )

        # Migrate: remove legacy single credit score entity if it exists
        old_entity_id = ent_reg.async_get_entity_id(
            "sensor", DOMAIN, f"{DOMAIN}_{unique_id}_credit_score"
        )
        if old_entity_id:
            _LOGGER.debug("Removing legacy credit score entity %s", old_entity_id)
            ent_reg.async_remove(old_entity_id)

    if options.get(CONF_ENABLE_HOLDINGS, False):
        holdings_data = coordinator.data.get("holdings", {})
        for account_id, holding_info in holdings_data.items():
            account = holding_info.get("account", {})
            holdings_raw = holding_info.get("holdings", {})
            edges = (
                holdings_raw.get("portfolio", {})
                .get("aggregateHoldings", {})
                .get("edges", [])
            )
            for edge in edges:
                node = edge.get("node", {})
                security = node.get("security")
                if security is None:
                    continue
                sensors.append(
                    MonarchHoldingSensor(
                        coordinator, node, account, unique_id
                    )
                )

    if options.get(CONF_ENABLE_AGGREGATED_HOLDINGS, False):
        holdings_data = coordinator.data.get("holdings", {})
        # Group holdings by ticker across all accounts
        aggregated: dict[str, dict] = {}
        for holding_info in holdings_data.values():
            account = holding_info.get("account", {})
            holdings_raw = holding_info.get("holdings", {})
            edges = (
                holdings_raw.get("portfolio", {})
                .get("aggregateHoldings", {})
                .get("edges", [])
            )
            for edge in edges:
                node = edge.get("node", {})
                security = node.get("security")
                if security is None:
                    continue
                ticker = security.get("ticker", "")
                if not ticker:
                    continue
                if ticker not in aggregated:
                    aggregated[ticker] = {
                        "ticker": ticker,
                        "security_name": security.get("name", ticker),
                        "security_type": security.get("typeDisplay"),
                        "current_price": security.get("currentPrice"),
                        "one_day_change_percent": security.get(
                            "oneDayChangePercent"
                        ),
                        "one_day_change_dollars": security.get(
                            "oneDayChangeDollars"
                        ),
                        "total_value": 0.0,
                        "quantity": 0.0,
                        "basis": 0.0,
                        "accounts": [],
                    }
                agg = aggregated[ticker]
                agg["total_value"] += node.get("totalValue") or 0.0
                agg["quantity"] += node.get("quantity") or 0.0
                agg["basis"] += node.get("basis") or 0.0
                agg["accounts"].append(account.get("displayName", ""))

        for ticker, agg_data in aggregated.items():
            sensors.append(
                MonarchAggregatedHoldingSensor(
                    coordinator, agg_data, unique_id
                )
            )

    async_add_entities(sensors, True)


class MonarchMoneyCategorySensor(CoordinatorEntity, SensorEntity):
    """Monarch Money category sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, category, unique_id) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context=category)
        self._account_type = SENSOR_TYPES_GROUP[category]["type"]
        group = SENSOR_TYPES_GROUP[category]["group"]
        prefix = GROUP_PREFIX[group]
        display_name = CATEGORY_DISPLAY_OVERRIDE.get(category, category)
        self._attr_name = f"{prefix} {display_name}"
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
            name="Monarch",
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
        self._attr_name = "Summary Net Worth"
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
            name="Monarch",
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
        self._attr_name = "Cashflow Savings This Month"
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_cash_flow_this_month"
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
            name="Monarch",
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
        self._attr_name = "Cashflow Income This Month"
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_income_this_month"
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
            name="Monarch",
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
        self._attr_name = "Cashflow Expenses This Month"
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_expenses_this_month"
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
            name="Monarch",
            manufacturer="Monarch Money",
            model="Financial Account",
        )


class MonarchCreditScoreSensor(CoordinatorEntity, SensorEntity):
    """Monarch Money credit score sensor for a specific household member."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, unique_id, user_id, user_name) -> None:
        """Initialize the credit score sensor."""
        super().__init__(coordinator)
        self._user_id = user_id
        self._user_name = user_name
        self._state = None
        self._reported_date = None
        self._previous_score = None
        self._score_change = None
        self._attr_name = f"Credit Score ({user_name})"
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_credit_score_{user_id}"
        self._id = unique_id
        self._attr_icon = "mdi:credit-card-check"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        return self._state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        update_data = self.coordinator.data
        if not update_data:
            return

        credit_data = update_data.get("credit_history", {})
        all_snapshots = credit_data.get("creditScoreSnapshots") or []

        # Filter snapshots for this user
        snapshots = [
            s for s in all_snapshots
            if s.get("user", {}).get("id") == self._user_id
        ]

        if not snapshots:
            return

        # Sort by date to ensure we get the most recent
        sorted_snapshots = sorted(
            snapshots,
            key=lambda s: s.get("reportedDate", ""),
        )

        latest = sorted_snapshots[-1]
        self._state = latest.get("score")
        self._reported_date = latest.get("reportedDate")

        if len(sorted_snapshots) >= 2:
            previous = sorted_snapshots[-2]
            self._previous_score = previous.get("score")
            if self._state is not None and self._previous_score is not None:
                self._score_change = self._state - self._previous_score
        else:
            self._previous_score = None
            self._score_change = None

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            "user_name": self._user_name,
            "reported_date": self._reported_date,
            "previous_score": self._previous_score,
            "score_change": self._score_change,
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._id)},
            name="Monarch",
            manufacturer="Monarch Money",
            model="Financial Account",
        )


class MonarchHoldingSensor(CoordinatorEntity, SensorEntity):
    """Monarch Money investment holding sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, holding_node, account, unique_id) -> None:
        """Initialize the holding sensor."""
        super().__init__(coordinator)
        self._holding_id = holding_node.get("id")
        self._account_id = account.get("id")
        self._account_name = account.get("displayName", "")

        security = holding_node.get("security", {})
        self._ticker = security.get("ticker", "")
        security_name = security.get("name", self._ticker)

        self._attr_name = f"Holding {self._ticker or security_name} ({self._account_name})"
        self._attr_unique_id = (
            f"{DOMAIN}_{unique_id}_holding_acct_{self._account_id}_{self._holding_id}"
        )
        self._id = unique_id
        self._attr_native_unit_of_measurement = "USD"
        self._attr_icon = "mdi:chart-line"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL

        self._state = None
        self._attrs: dict = {}

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        return self._state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        update_data = self.coordinator.data
        if not update_data:
            return

        holdings_data = update_data.get("holdings", {})
        account_holdings = holdings_data.get(self._account_id, {})
        holdings_raw = account_holdings.get("holdings", {})
        edges = (
            holdings_raw.get("portfolio", {})
            .get("aggregateHoldings", {})
            .get("edges", [])
        )

        for edge in edges:
            node = edge.get("node", {})
            if node.get("id") == self._holding_id:
                self._state = node.get("totalValue")
                security = node.get("security") or {}
                self._attrs = {
                    "ticker": security.get("ticker"),
                    "quantity": node.get("quantity"),
                    "cost_basis": node.get("basis"),
                    "current_price": security.get("currentPrice"),
                    "security_type": security.get("typeDisplay"),
                    "one_day_change_percent": security.get(
                        "oneDayChangePercent"
                    ),
                    "one_day_change_dollars": security.get(
                        "oneDayChangeDollars"
                    ),
                    "account_name": self._account_name,
                }
                # Calculate gain/loss
                basis = node.get("basis")
                total_value = node.get("totalValue")
                if basis is not None and total_value is not None:
                    self._attrs["gain_loss"] = round(total_value - basis, 2)
                    if basis > 0:
                        self._attrs["gain_loss_percent"] = round(
                            ((total_value - basis) / basis) * 100, 2
                        )
                break

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return self._attrs

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._id)},
            name="Monarch",
            manufacturer="Monarch Money",
            model="Financial Account",
        )


class MonarchAggregatedHoldingSensor(CoordinatorEntity, SensorEntity):
    """Monarch Money aggregated investment holding sensor (across all accounts)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, agg_data, unique_id) -> None:
        """Initialize the aggregated holding sensor."""
        super().__init__(coordinator)
        self._ticker = agg_data["ticker"]
        self._attr_name = f"Holding {self._ticker} Total"
        self._attr_unique_id = (
            f"{DOMAIN}_{unique_id}_holding_agg_{self._ticker}"
        )
        self._id = unique_id
        self._attr_native_unit_of_measurement = "USD"
        self._attr_icon = "mdi:chart-areaspline"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL

        self._state = None
        self._attrs: dict = {}

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        return self._state

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        update_data = self.coordinator.data
        if not update_data:
            return

        holdings_data = update_data.get("holdings", {})

        total_value = 0.0
        total_quantity = 0.0
        total_basis = 0.0
        accounts: list[str] = []
        current_price = None
        security_type = None
        one_day_change_percent = None
        one_day_change_dollars = None

        for holding_info in holdings_data.values():
            account = holding_info.get("account", {})
            holdings_raw = holding_info.get("holdings", {})
            edges = (
                holdings_raw.get("portfolio", {})
                .get("aggregateHoldings", {})
                .get("edges", [])
            )
            for edge in edges:
                node = edge.get("node", {})
                security = node.get("security")
                if security is None:
                    continue
                if security.get("ticker") == self._ticker:
                    total_value += node.get("totalValue") or 0.0
                    total_quantity += node.get("quantity") or 0.0
                    total_basis += node.get("basis") or 0.0
                    accounts.append(account.get("displayName", ""))
                    # Price/type is the same across accounts
                    current_price = security.get("currentPrice")
                    security_type = security.get("typeDisplay")
                    one_day_change_percent = security.get(
                        "oneDayChangePercent"
                    )
                    one_day_change_dollars = security.get(
                        "oneDayChangeDollars"
                    )

        self._state = round(total_value, 2)
        self._attrs = {
            "ticker": self._ticker,
            "quantity": round(total_quantity, 4),
            "cost_basis": round(total_basis, 2),
            "current_price": current_price,
            "security_type": security_type,
            "one_day_change_percent": one_day_change_percent,
            "one_day_change_dollars": one_day_change_dollars,
            "accounts": accounts,
            "account_count": len(accounts),
        }
        if total_basis > 0:
            self._attrs["gain_loss"] = round(total_value - total_basis, 2)
            self._attrs["gain_loss_percent"] = round(
                ((total_value - total_basis) / total_basis) * 100, 2
            )

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return self._attrs

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._id)},
            name="Monarch",
            manufacturer="Monarch Money",
            model="Financial Account",
        )

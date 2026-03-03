"""Sensor platform for Monarch Money integration."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import (
    CONF_ENABLE_AGGREGATED_HOLDINGS,
    CONF_ENABLE_CREDIT_SCORE,
    CONF_ENABLE_HOLDINGS,
    DOMAIN,
)
from ..update_coordinator import MonarchCoordinator
from .category import MonarchMoneyCategorySensor
from .cashflow import MonarchMoneyCashFlowSensor
from .constants import ATTR_OTHER, SENSOR_TYPES_GROUP
from .credit_score import MonarchCreditScoreSensor
from .expense import MonarchMoneyExpenseSensor
from .holding import MonarchHoldingSensor
from .aggregated_holding import MonarchAggregatedHoldingSensor
from .income import MonarchMoneyIncomeSensor
from .net_worth import MonarchMoneyNetWorthSensor

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Monarch Money sensors from a config entry."""
    coordinator: MonarchCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    unique_id = config_entry.unique_id
    options = config_entry.options
    data = coordinator.data

    # Check which account types have data for conditional sensors
    account_types_present: set[str] = set()
    if data:
        account_types_present = {a.account_type.name for a in data.accounts}

    sensors: list[SensorEntity] = []
    for category in SENSOR_TYPES_GROUP:
        if category == ATTR_OTHER and "other" not in account_types_present:
            continue
        sensors.append(MonarchMoneyCategorySensor(coordinator, category, unique_id))

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

    # Optional: Credit score sensors (per household user)
    if options.get(CONF_ENABLE_CREDIT_SCORE, False) and data and data.credit_history:
        credit = data.credit_history
        user_names = {u.id: u.display_name for u in credit.household_users}
        user_ids_with_scores = {s.user_id for s in credit.snapshots if s.user_id}

        for user_id in user_ids_with_scores:
            display_name = user_names.get(user_id, "Unknown")
            sensors.append(
                MonarchCreditScoreSensor(coordinator, unique_id, user_id, display_name)
            )

        # Remove legacy single credit score entity
        old_entity_id = ent_reg.async_get_entity_id(
            "sensor", DOMAIN, f"{DOMAIN}_{unique_id}_credit_score"
        )
        if old_entity_id:
            _LOGGER.debug("Removing legacy credit score entity %s", old_entity_id)
            ent_reg.async_remove(old_entity_id)

    # Optional: Per-account holding sensors
    if options.get(CONF_ENABLE_HOLDINGS, False) and data:
        for acct_holdings in data.holdings:
            for holding in acct_holdings.holdings:
                sensors.append(
                    MonarchHoldingSensor(
                        coordinator, holding, acct_holdings.account, unique_id
                    )
                )

    # Optional: Aggregated holding sensors (grouped by ticker)
    if options.get(CONF_ENABLE_AGGREGATED_HOLDINGS, False) and data:
        aggregated: dict[str, dict] = {}
        for acct_holdings in data.holdings:
            for holding in acct_holdings.holdings:
                ticker = holding.security.ticker
                if not ticker:
                    continue
                if ticker not in aggregated:
                    aggregated[ticker] = {
                        "ticker": ticker,
                        "security_name": holding.security.name,
                        "security_type": holding.security.type_display,
                        "current_price": holding.security.current_price,
                        "one_day_change_percent": holding.security.one_day_change_percent,
                        "one_day_change_dollars": holding.security.one_day_change_dollars,
                        "total_value": 0.0,
                        "quantity": 0.0,
                        "basis": 0.0,
                        "accounts": [],
                    }
                agg = aggregated[ticker]
                agg["total_value"] += holding.total_value or 0.0
                agg["quantity"] += holding.quantity or 0.0
                agg["basis"] += holding.basis or 0.0
                agg["accounts"].append(acct_holdings.account.display_name)

        for agg_data in aggregated.values():
            sensors.append(
                MonarchAggregatedHoldingSensor(coordinator, agg_data, unique_id)
            )

    async_add_entities(sensors, True)

"""Config flow for Monarch Money integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from monarchmoney import MonarchMoney, RequireMFAException, LoginFailedException

from .util import monarch_login
from .const import (
    CONF_ENABLE_AGGREGATED_HOLDINGS,
    CONF_ENABLE_CREDIT_SCORE,
    CONF_ENABLE_HOLDINGS,
    CONF_ENABLE_RECURRING,
    CONF_MFA_CODE,
    CONF_MFA_SECRET,
    CONF_TIMEOUT,
    CONF_TOKEN,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    VALUES_SCAN_INTERVAL,
    VALUES_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class RequireMFA(HomeAssistantError):
    """Error to indicate MFA is required."""


class RateLimited(HomeAssistantError):
    """Error to indicate rate limiting."""


CREDENTIALS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(
            CONF_MFA_SECRET, description="MFA Secret Key (Optional - for automatic MFA)"
        ): str,
    }
)

MFA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MFA_CODE): str,
    }
)

MFA_SETUP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_MFA_SECRET): str,
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.In(
            VALUES_SCAN_INTERVAL
        ),
        vol.Required(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.In(VALUES_TIMEOUT),
        vol.Optional(CONF_ENABLE_CREDIT_SCORE, default=False): bool,
        vol.Optional(CONF_ENABLE_HOLDINGS, default=False): bool,
        vol.Optional(CONF_ENABLE_AGGREGATED_HOLDINGS, default=False): bool,
        vol.Optional(CONF_ENABLE_RECURRING, default=False): bool,
    }
)


class MonarchConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Monarch Money."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._existing_entry: dict[str, Any] | None = None
        self._user_input: dict[str, Any] = {}
        self._description_placeholders: dict[str, str] | None = None
        self._api_token: str | None = None

    def _get_schema(self, step_id: str) -> vol.Schema:
        """Get the schema for the given step."""
        if step_id == "user":
            return CREDENTIALS_SCHEMA
        elif step_id == "mfa":
            return MFA_SCHEMA
        elif step_id == "mfa_setup":
            return MFA_SETUP_SCHEMA
        if step_id == "reauth_confirm":
            return vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(
                        CONF_MFA_SECRET,
                        description="MFA Secret Key (Optional - for automatic MFA)",
                    ): str,
                }
            )
        return vol.Schema({vol.Required(CONF_PASSWORD): str})

    @staticmethod
    def _is_mfa_error(error_str: str) -> bool:
        """Check if an error string indicates MFA is required."""
        return any(
            keyword in error_str
            for keyword in ("401", "unauthorized", "mfa", "multi-factor", "authentication")
        )

    def _update_mfa_secret(self, user_input: dict[str, Any]) -> None:
        """Update MFA secret in _user_input from form data."""
        if CONF_MFA_SECRET in user_input and user_input[CONF_MFA_SECRET].strip():
            self._user_input[CONF_MFA_SECRET] = user_input[CONF_MFA_SECRET].strip()
        else:
            self._user_input.pop(CONF_MFA_SECRET, None)

    async def _test_connection_and_set_token(self) -> None:
        """Test connection and save session token."""
        api = MonarchMoney()

        try:
            await monarch_login(
                api,
                self._user_input[CONF_EMAIL],
                self._user_input[CONF_PASSWORD],
                self._user_input.get(CONF_MFA_SECRET),
            )
        except RequireMFAException:
            _LOGGER.info(
                "MFA required for Monarch Money authentication (caught during login)"
            )
            raise RequireMFA
        except LoginFailedException as exc:
            _LOGGER.error("Failed to login to Monarch Money")
            error_str = str(exc).lower()
            # Check for rate limiting (429 Too Many Requests)
            if "429" in error_str or "too many requests" in error_str:
                _LOGGER.warning("Rate limited by Monarch Money API")
                raise RateLimited from exc
            # Check if this is an MFA-related error
            elif self._is_mfa_error(error_str):
                _LOGGER.info("Detected possible MFA requirement from login error")
                raise RequireMFA
            else:
                raise InvalidAuth from exc
        except Exception as exc:
            _LOGGER.error("Failed to login to Monarch Money")
            # Check if this is an MFA-related error by examining the error message
            error_str = str(exc).lower()
            if self._is_mfa_error(error_str):
                _LOGGER.info("Detected possible MFA requirement from login error")
                raise RequireMFA
            raise InvalidAuth from exc

        _LOGGER.info("Successfully authenticated with Monarch Money")
        self._api_token = api.token

    async def _test_mfa_and_set_token(self) -> None:
        """Test MFA code and save session token."""
        try:
            api = MonarchMoney()
            await api.multi_factor_authenticate(
                self._user_input[CONF_EMAIL],
                self._user_input[CONF_PASSWORD],
                self._user_input[CONF_MFA_CODE],
            )
            _LOGGER.info("Successfully authenticated with Monarch Money using MFA")
            self._api_token = api.token

        except LoginFailedException as exc:
            _LOGGER.error("Failed to authenticate with Monarch Money using MFA")
            error_str = str(exc).lower()
            # Check for rate limiting (429 Too Many Requests)
            if "429" in error_str or "too many requests" in error_str:
                _LOGGER.warning("Rate limited by Monarch Money API during MFA")
                raise RateLimited from exc
            else:
                raise InvalidAuth from exc
        except Exception as exc:
            _LOGGER.error("Failed to authenticate with Monarch Money using MFA")
            raise InvalidAuth from exc

    def _show_setup_form(
        self,
        user_input: dict[str, Any] | None = None,
        errors: dict[str, str] | None = None,
        step_id: str = "user",
    ) -> ConfigFlowResult:
        """Show the setup form to the user."""
        if user_input is None:
            user_input = {}

        return self.async_show_form(
            step_id=step_id,
            data_schema=self._get_schema(step_id),
            errors=errors or {},
            description_placeholders=self._description_placeholders,
        )

    async def _validate_and_create_entry(
        self, user_input: dict[str, Any], step_id: str
    ) -> ConfigFlowResult:
        """Check if config is valid and create entry if so."""
        if step_id == "mfa":
            self._user_input[CONF_MFA_CODE] = user_input[CONF_MFA_CODE]
        elif step_id == "mfa_setup":
            self._user_input[CONF_EMAIL] = user_input[CONF_EMAIL]
            self._user_input[CONF_PASSWORD] = user_input[CONF_PASSWORD]
            self._update_mfa_secret(user_input)
        elif step_id == "reauth_confirm":
            # Handle reauth - password comes from user input, email from existing entry
            self._user_input[CONF_PASSWORD] = user_input[CONF_PASSWORD]
            self._update_mfa_secret(user_input)

            if self._existing_entry:
                self._user_input[CONF_EMAIL] = self._existing_entry[CONF_EMAIL]
        else:
            # Main user flow
            self._user_input[CONF_EMAIL] = user_input[CONF_EMAIL]
            self._user_input[CONF_PASSWORD] = user_input[CONF_PASSWORD]
            self._update_mfa_secret(user_input)

        if self.unique_id is None:
            await self.async_set_unique_id(self._user_input[CONF_EMAIL])
            self._abort_if_unique_id_configured()

        try:
            if step_id == "mfa":
                await self._test_mfa_and_set_token()
            else:
                await self._test_connection_and_set_token()
        except RequireMFA:
            if step_id == "reauth_confirm":
                return await self.async_step_reauth_mfa()
            else:
                return await self.async_step_mfa()
        except RateLimited:
            return self.async_show_form(
                step_id=step_id,
                data_schema=self._get_schema(step_id),
                errors={"base": "rate_limited"},
            )
        except InvalidAuth:
            return self.async_show_form(
                step_id=step_id,
                data_schema=self._get_schema(step_id),
                errors={"base": "invalid_auth"},
            )
        except Exception:
            _LOGGER.exception("Unexpected error during authentication")
            return self.async_show_form(
                step_id=step_id,
                data_schema=self._get_schema(step_id),
                errors={"base": "cannot_connect"},
            )

        # Include the auth token in config entry data
        if self._api_token:
            self._user_input[CONF_TOKEN] = self._api_token

        if self.source == config_entries.SOURCE_REAUTH:
            # Handle re-authentication (both reauth_confirm and mfa during reauth)
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(),
                data_updates=self._user_input,
            )

        return self.async_create_entry(
            title=self._user_input[CONF_EMAIL], data=self._user_input
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self._show_setup_form()

        return await self._validate_and_create_entry(user_input, "user")

    async def async_step_mfa(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle MFA step."""
        if user_input is None:
            return self._show_setup_form(step_id="mfa")

        return await self._validate_and_create_entry(user_input, "mfa")

    async def async_step_mfa_setup(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle MFA setup step with secret key."""
        if user_input is None:
            return self._show_setup_form(step_id="mfa_setup")

        return await self._validate_and_create_entry(user_input, "mfa_setup")

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle configuration by re-auth."""
        await self.async_set_unique_id(entry_data[CONF_EMAIL])
        self._existing_entry = {**entry_data}
        # Initialize _user_input with only essential data, not MFA secret
        self._user_input = {
            CONF_EMAIL: entry_data[CONF_EMAIL],
            CONF_PASSWORD: entry_data[CONF_PASSWORD],
        }
        self._description_placeholders = {
            CONF_EMAIL: entry_data[CONF_EMAIL],
        }
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Handle re-auth completion."""
        if user_input is None:
            return self._show_setup_form(step_id="reauth_confirm")

        return await self._validate_and_create_entry(user_input, "reauth_confirm")

    async def async_step_reauth_mfa(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle MFA step during reauth."""
        if user_input is None:
            return self._show_setup_form(step_id="mfa")

        return await self._validate_and_create_entry(user_input, "mfa")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Define the config flow to handle options."""
        return MonarchOptionsFlowHandler(config_entry)


class MonarchOptionsFlowHandler(OptionsFlow):
    """Handle Monarch Money options flow."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.entry = entry

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.entry.options
            ),
        )

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
from monarchmoney import MonarchMoney, RequireMFAException

from .const import (
    CONF_MFA_CODE,
    CONF_MFA_SECRET,
    CONF_TIMEOUT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    SESSION_FILE,
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


CREDENTIALS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
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
    }
)


class MonarchConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Monarch Money."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._existing_entry: dict[str, Any] | None = None
        self._user_input: dict[str, Any] = {}
        self._description_placeholders: dict[str, str] | None = None

    def _get_schema(self, step_id: str) -> vol.Schema:
        """Get the schema for the given step."""
        if step_id == "user":
            return CREDENTIALS_SCHEMA
        elif step_id == "mfa":
            return MFA_SCHEMA
        elif step_id == "mfa_setup":
            return MFA_SETUP_SCHEMA
        return vol.Schema({vol.Required(CONF_PASSWORD): str})

    async def _test_connection_and_set_token(self) -> None:
        """Test connection and save session token."""
        session_file_path = self.hass.config.path(SESSION_FILE)
        api = MonarchMoney()

        try:
            # Try login with MFA secret if provided
            if CONF_MFA_SECRET in self._user_input:
                await api.login(
                    email=self._user_input[CONF_EMAIL],
                    password=self._user_input[CONF_PASSWORD],
                    save_session=False,
                    use_saved_session=False,
                    mfa_secret_key=self._user_input[CONF_MFA_SECRET],
                )
            else:
                await api.login(
                    self._user_input[CONF_EMAIL], self._user_input[CONF_PASSWORD]
                )
        except RequireMFAException:
            _LOGGER.info(
                "MFA required for Monarch Money authentication (caught during login)"
            )
            raise RequireMFA
        except Exception as exc:
            _LOGGER.exception("Failed to login to Monarch Money")
            # Check if this is an MFA-related error by examining the error message
            error_str = str(exc).lower()
            if (
                "401" in error_str
                or "unauthorized" in error_str
                or "mfa" in error_str
                or "multi-factor" in error_str
                or "authentication" in error_str
            ):
                _LOGGER.info("Detected possible MFA requirement from login error")
                raise RequireMFA
            raise InvalidAuth from exc

        try:
            # Test API access by getting account information
            await api.get_accounts()
            _LOGGER.info("Successfully authenticated with Monarch Money")

            # Save the session token using executor to avoid blocking I/O
            await self.hass.async_add_executor_job(api.save_session, session_file_path)

        except RequireMFAException:
            _LOGGER.info(
                "MFA required for Monarch Money authentication (caught during API call)"
            )
            raise RequireMFA
        except Exception as exc:
            _LOGGER.exception("Failed to access Monarch Money API after login")

            # Check if this is an MFA-related error by examining the error message
            error_str = str(exc).lower()
            if (
                "401" in error_str
                or "unauthorized" in error_str
                or "mfa" in error_str
                or "multi-factor" in error_str
                or "authentication" in error_str
            ):
                _LOGGER.info("Detected possible MFA requirement from API access error")
                raise RequireMFA

            raise InvalidAuth from exc

    async def _test_mfa_and_set_token(self) -> None:
        """Test MFA code and save session token."""
        session_file_path = self.hass.config.path(SESSION_FILE)
        try:
            api = MonarchMoney()
            await api.multi_factor_authenticate(
                self._user_input[CONF_EMAIL],
                self._user_input[CONF_PASSWORD],
                self._user_input[CONF_MFA_CODE],
            )

            # Test API access by getting account information
            await api.get_accounts()
            _LOGGER.info("Successfully authenticated with Monarch Money using MFA")

            # Save the session token using executor to avoid blocking I/O
            await self.hass.async_add_executor_job(api.save_session, session_file_path)

        except Exception as exc:
            _LOGGER.exception("Failed to authenticate with Monarch Money using MFA")
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
            if CONF_MFA_SECRET in user_input:
                self._user_input[CONF_MFA_SECRET] = user_input[CONF_MFA_SECRET]
        else:
            self._user_input[CONF_PASSWORD] = user_input[CONF_PASSWORD]

            extra_inputs = user_input
            if self._existing_entry:
                extra_inputs = self._existing_entry
            self._user_input[CONF_EMAIL] = extra_inputs[CONF_EMAIL]

        if self.unique_id is None:
            await self.async_set_unique_id(self._user_input[CONF_EMAIL])
            self._abort_if_unique_id_configured()

        try:
            if step_id == "mfa":
                await self._test_mfa_and_set_token()
            else:
                await self._test_connection_and_set_token()
        except RequireMFA:
            return await self.async_step_mfa()
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

        if step_id in ("user", "mfa", "mfa_setup"):
            return self.async_create_entry(
                title=self._user_input[CONF_EMAIL], data=self._user_input
            )

        # Handle re-authentication
        entry = await self.async_set_unique_id(self.unique_id)
        if entry:
            self.hass.config_entries.async_update_entry(entry, data=self._user_input)
            await self.hass.config_entries.async_reload(entry.entry_id)
        return self.async_abort(reason="reauth_successful")

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
        self._description_placeholders = {
            CONF_EMAIL: entry_data[CONF_EMAIL],
            CONF_PASSWORD: entry_data[CONF_PASSWORD],
        }
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Handle re-auth completion."""
        if user_input is None:
            return self._show_setup_form(step_id="reauth_confirm")

        return await self._validate_and_create_entry(user_input, "reauth_confirm")

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

        return self.async_show_form(step_id="init", data_schema=OPTIONS_SCHEMA)

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

from .const import (
    CONF_MFA_CODE,
    CONF_MFA_SECRET,
    CONF_TIMEOUT,
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

    async def _test_connection_and_set_token(self) -> None:
        """Test connection and save session token."""
        api = MonarchMoney()

        try:
            # Try login with MFA secret if provided
            if CONF_MFA_SECRET in self._user_input:
                await api.login(
                    email=self._user_input[CONF_EMAIL],
                    password=self._user_input[CONF_PASSWORD],
                    save_session=False,  # Disable automatic session saving to avoid blocking I/O
                    use_saved_session=False,  # Don't use existing session for fresh login
                    mfa_secret_key=self._user_input[CONF_MFA_SECRET],
                )
            else:
                await api.login(
                    email=self._user_input[CONF_EMAIL],
                    password=self._user_input[CONF_PASSWORD],
                    save_session=False,  # Disable automatic session saving to avoid blocking I/O
                    use_saved_session=False,  # Don't use existing session for fresh login
                )
        except RequireMFAException:
            _LOGGER.info(
                "MFA required for Monarch Money authentication (caught during login)"
            )
            raise RequireMFA
        except LoginFailedException as exc:
            _LOGGER.exception("Failed to login to Monarch Money")
            error_str = str(exc).lower()
            # Check for rate limiting (429 Too Many Requests)
            if "429" in error_str or "too many requests" in error_str:
                _LOGGER.warning("Rate limited by Monarch Money API")
                raise RateLimited from exc
            # Check if this is an MFA-related error
            elif (
                "401" in error_str
                or "unauthorized" in error_str
                or "mfa" in error_str
                or "multi-factor" in error_str
                or "authentication" in error_str
            ):
                _LOGGER.info("Detected possible MFA requirement from login error")
                raise RequireMFA
            else:
                raise InvalidAuth from exc
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

            # Save session manually using executor to avoid blocking I/O
            await self.hass.async_add_executor_job(api.save_session)
            _LOGGER.debug("Session saved successfully")

        except RequireMFAException:
            _LOGGER.info(
                "MFA required for Monarch Money authentication (caught during API call)"
            )
            raise RequireMFA
        except LoginFailedException as exc:
            _LOGGER.exception("Failed to access Monarch Money API after login")
            error_str = str(exc).lower()
            # Check for rate limiting (429 Too Many Requests)
            if "429" in error_str or "too many requests" in error_str:
                _LOGGER.warning("Rate limited by Monarch Money API")
                raise RateLimited from exc
            # Check if this is an MFA-related error
            elif (
                "401" in error_str
                or "unauthorized" in error_str
                or "mfa" in error_str
                or "multi-factor" in error_str
                or "authentication" in error_str
            ):
                _LOGGER.info("Detected possible MFA requirement from API access error")
                raise RequireMFA
            else:
                raise InvalidAuth from exc
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

            # Save the session using the library's method with executor
            await self.hass.async_add_executor_job(api.save_session)

        except LoginFailedException as exc:
            _LOGGER.exception("Failed to authenticate with Monarch Money using MFA")
            error_str = str(exc).lower()
            # Check for rate limiting (429 Too Many Requests)
            if "429" in error_str or "too many requests" in error_str:
                _LOGGER.warning("Rate limited by Monarch Money API during MFA")
                raise RateLimited from exc
            else:
                raise InvalidAuth from exc
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
            # Only add MFA secret if explicitly provided and not empty
            if CONF_MFA_SECRET in user_input and user_input[CONF_MFA_SECRET].strip():
                self._user_input[CONF_MFA_SECRET] = user_input[CONF_MFA_SECRET].strip()
            else:
                # Remove MFA secret if it exists in current config
                self._user_input.pop(CONF_MFA_SECRET, None)
        elif step_id == "reauth_confirm":
            # Handle reauth - password comes from user input, email from existing entry
            self._user_input[CONF_PASSWORD] = user_input[CONF_PASSWORD]

            # Only add MFA secret if explicitly provided and not empty during reauth
            if CONF_MFA_SECRET in user_input and user_input[CONF_MFA_SECRET].strip():
                self._user_input[CONF_MFA_SECRET] = user_input[CONF_MFA_SECRET].strip()
            else:
                # Remove MFA secret if it exists in current config
                self._user_input.pop(CONF_MFA_SECRET, None)

            if self._existing_entry:
                self._user_input[CONF_EMAIL] = self._existing_entry[CONF_EMAIL]
        else:
            # Main user flow
            self._user_input[CONF_EMAIL] = user_input[CONF_EMAIL]
            self._user_input[CONF_PASSWORD] = user_input[CONF_PASSWORD]

            # Only add MFA secret if explicitly provided and not empty in main user flow
            if CONF_MFA_SECRET in user_input and user_input[CONF_MFA_SECRET].strip():
                self._user_input[CONF_MFA_SECRET] = user_input[CONF_MFA_SECRET].strip()
            else:
                # Remove MFA secret if it exists in current config
                self._user_input.pop(CONF_MFA_SECRET, None)

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

        if step_id in ("user", "mfa_setup"):
            return self.async_create_entry(
                title=self._user_input[CONF_EMAIL], data=self._user_input
            )

        # Handle re-authentication (both reauth_confirm and mfa during reauth)
        if step_id in ("reauth_confirm", "mfa"):
            entry = await self.async_set_unique_id(self.unique_id)
            if entry:
                self.hass.config_entries.async_update_entry(
                    entry, data=self._user_input
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
            return self.async_abort(reason="reauth_successful")

        # Fallback for other cases
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
        # Initialize _user_input with only essential data, not MFA secret
        self._user_input = {
            CONF_EMAIL: entry_data[CONF_EMAIL],
            CONF_PASSWORD: entry_data[CONF_PASSWORD],
        }
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

        return self.async_show_form(step_id="init", data_schema=OPTIONS_SCHEMA)

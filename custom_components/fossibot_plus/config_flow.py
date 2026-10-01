"""Config flow for FOSSiBOT."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FossibotApiClient, FossibotAuthError, FossibotConnectionError
from .const import (
    CHARGE_POWER_LIMITS,
    CONF_EMAIL,
    CONF_MODEL,
    CONF_PASSWORD,
    DOMAIN,
    MODEL_CUSTOM,
    MODEL_F1800,
    MODEL_F3000,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

STEP_MODEL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MODEL, default=MODEL_F1800): vol.In(
            [MODEL_F1800, MODEL_F3000, MODEL_CUSTOM]
        ),
    }
)


class FossibotConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a FOSSiBOT config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = FossibotApiClient(
                session, user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
            )
            try:
                await api.async_login()
                await api.async_get_devices()
            except FossibotAuthError as err:
                _LOGGER.debug("FOSSiBOT auth rejected: %s", err)
                errors["base"] = "invalid_auth"
            except FossibotConnectionError as err:
                _LOGGER.debug("FOSSiBOT connection failed: %s", err)
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating FOSSiBOT credentials")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
                self._abort_if_unique_id_configured()
                self._data = dict(user_input)
                return await self.async_step_model()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_model(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self._data[CONF_MODEL] = user_input[CONF_MODEL]
            return self.async_create_entry(
                title=self._data[CONF_EMAIL], data=self._data
            )
        return self.async_show_form(
            step_id="model", data_schema=STEP_MODEL_SCHEMA
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return FossibotOptionsFlow(config_entry)


class FossibotOptionsFlow(config_entries.OptionsFlow):
    """Allow changing the model after initial setup."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        current_model = self._config_entry.data.get(CONF_MODEL, MODEL_F1800)
        if user_input is not None:
            # Store in options; __init__.py reads options first, then data
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MODEL, default=current_model): vol.In(
                        [MODEL_F1800, MODEL_F3000, MODEL_CUSTOM]
                    )
                }
            ),
        )

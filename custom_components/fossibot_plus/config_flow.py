"""Config flow for FOSSiBOT."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FossibotApiClient, FossibotAuthError, FossibotConnectionError
from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class FossibotConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a FOSSiBOT config flow."""

    VERSION = 1

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
            except Exception:  # noqa: BLE001 - surface anything unexpected, don't crash the flow
                _LOGGER.exception("Unexpected error validating FOSSiBOT credentials")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_EMAIL], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

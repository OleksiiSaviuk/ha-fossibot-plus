"""The FOSSiBOT Power Station integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FossibotApiClient
from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN
from .coordinator import FossibotCoordinator

PLATFORMS = ["sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Reuse HA's shared session instead of opening a new one - the source
    # spec's draft code created its own aiohttp.ClientSession, which would
    # leak connections every time the entry reloads.
    session = async_get_clientsession(hass)
    api = FossibotApiClient(session, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
    await api.async_login()
    devices = await api.async_get_devices()

    coordinators: dict[str, FossibotCoordinator] = {}
    for device in devices:
        sn_code = device["snCode"]
        coordinator = FossibotCoordinator(
            hass, api, sn_code, device.get("deviceName", sn_code)
        )
        await coordinator.async_start()
        coordinators[sn_code] = coordinator

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api,
        "coordinators": coordinators,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        for coordinator in data["coordinators"].values():
            await coordinator.async_stop()
    return unloaded

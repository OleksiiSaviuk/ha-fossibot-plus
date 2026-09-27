"""The FOSSiBOT Power Station integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

from .api import FossibotApiClient, FossibotAuthError, FossibotConnectionError
from .const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    DEVICE_STATUS_POLL_INTERVAL,
    DOMAIN,
)
from .coordinator import FossibotCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "switch"]


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
        # Include the serial number in the device name so multiple stations
        # (different models or several of the same model) don't all show up
        # as an identical "Fossibot" in the HA device list.
        device_name = f"{device.get('deviceName', 'Fossibot')}-{sn_code}"
        coordinator = FossibotCoordinator(hass, api, sn_code, device_name)
        # "state" from user_device/list is the device's online/offline flag
        # (confirmed via a Charles capture: state:false while the station
        # was powered off/offline) - seed it before the first poll below.
        coordinator.set_online(bool(device.get("state", True)))
        await coordinator.async_start()
        coordinators[sn_code] = coordinator

    async def _async_refresh_online_status(_now=None) -> None:
        # Online/offline is a REST-only field, not part of the WS telemetry
        # frames, so it has to be polled separately on a timer.
        try:
            fresh_devices = await api.async_get_devices()
        except (FossibotAuthError, FossibotConnectionError) as err:
            _LOGGER.debug("Could not refresh FOSSiBOT online status: %s", err)
            return
        seen: set[str] = set()
        for device in fresh_devices:
            sn_code = device.get("snCode")
            coordinator = coordinators.get(sn_code)
            if coordinator is None:
                continue
            seen.add(sn_code)
            coordinator.set_online(bool(device.get("state", False)))
        # A device that has disappeared from the list entirely is treated
        # as offline too, rather than left showing its last-known state.
        for sn_code, coordinator in coordinators.items():
            if sn_code not in seen:
                coordinator.set_online(False)

    remove_status_listener = async_track_time_interval(
        hass, _async_refresh_online_status, DEVICE_STATUS_POLL_INTERVAL
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api,
        "coordinators": coordinators,
        "remove_status_listener": remove_status_listener,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        data["remove_status_listener"]()
        for coordinator in data["coordinators"].values():
            await coordinator.async_stop()
    return unloaded

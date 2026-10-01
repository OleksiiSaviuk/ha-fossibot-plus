"""Output and device-setting switches for the FOSSiBOT power station."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import FossibotApiClient
from .const import (
    DOMAIN,
    TAG_AC_STATE,
    TAG_DC_STATE,
    TAG_OUTPUT_MEMORY,
    TAG_SOUND,
    TAG_USB_STATE,
)
from .coordinator import FossibotCoordinator

_LOGGER = logging.getLogger(__name__)

# (key, tag, translation_key, name)
SWITCH_TYPES: tuple[tuple[str, str, str, str], ...] = (
    ("ac_output",      TAG_AC_STATE,      "ac_output",      "AC output"),
    ("dc_output",      TAG_DC_STATE,      "dc_output",      "DC output"),
    ("usb_output",     TAG_USB_STATE,     "usb_output",     "USB output"),
    ("sound",          TAG_SOUND,         "sound",          "Sound"),
    ("output_memory",  TAG_OUTPUT_MEMORY, "output_memory",  "Output memory"),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    api: FossibotApiClient = data["api"]
    entities = [
        FossibotSwitch(coordinator, api, key, tag, translation_key, name)
        for coordinator in data["coordinators"].values()
        for key, tag, translation_key, name in SWITCH_TYPES
    ]
    async_add_entities(entities)


class FossibotSwitch(CoordinatorEntity[FossibotCoordinator], SwitchEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FossibotCoordinator,
        api: FossibotApiClient,
        key: str,
        tag: str,
        translation_key: str,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._api = api
        self._tag = tag
        self.entity_description = SwitchEntityDescription(
            key=key, translation_key=translation_key, name=name
        )
        self._attr_unique_id = f"{coordinator.sn_code}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.sn_code)},
            name=coordinator.device_name,
            manufacturer="FOSSiBOT",
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.online

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None
        raw = self.coordinator.data.get(self._tag)
        return None if raw is None else bool(raw)

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_send(1)

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_send(0)

    async def _async_send(self, value: int) -> None:
        await self._api.async_send_control(self.coordinator.sn_code, self._tag, value)
        if self.coordinator.data is not None:
            new_data = dict(self.coordinator.data)
            new_data[self._tag] = value
            self.coordinator.async_set_updated_data(new_data)

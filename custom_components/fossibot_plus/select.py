"""LED mode select entity for the FOSSiBOT power station.

Tag 2600 controls the built-in LED lamp:
  0 = off
  1 = steady (Постійний)
  2 = SOS
  3 = strobe (Стробоскоп)

All four values confirmed from captured /ctrl/route requests and from live
WS telemetry (tag 2600 observed at 0, 1, 3 in the same session).
"""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import FossibotApiClient
from .const import DOMAIN, TAG_LED_MODE
from .coordinator import FossibotCoordinator

_LOGGER = logging.getLogger(__name__)

LED_OFF     = "off"
LED_STEADY  = "steady"
LED_SOS     = "sos"
LED_STROBE  = "strobe"

# value in TLV frame -> option string
_VALUE_TO_OPTION: dict[int, str] = {
    0: LED_OFF,
    1: LED_STEADY,
    2: LED_SOS,
    3: LED_STROBE,
}
_OPTION_TO_VALUE: dict[str, int] = {v: k for k, v in _VALUE_TO_OPTION.items()}

OPTIONS = [LED_OFF, LED_STEADY, LED_SOS, LED_STROBE]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    api: FossibotApiClient = data["api"]
    entities = [
        FossibotLedSelect(coordinator, api)
        for coordinator in data["coordinators"].values()
    ]
    async_add_entities(entities)


class FossibotLedSelect(CoordinatorEntity[FossibotCoordinator], SelectEntity):
    _attr_has_entity_name = True
    _attr_options = OPTIONS

    def __init__(
        self,
        coordinator: FossibotCoordinator,
        api: FossibotApiClient,
    ) -> None:
        super().__init__(coordinator)
        self._api = api
        self.entity_description = SelectEntityDescription(
            key="led_mode",
            translation_key="led_mode",
            name="LED mode",
        )
        self._attr_unique_id = f"{coordinator.sn_code}_led_mode"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.sn_code)},
            name=coordinator.device_name,
            manufacturer="FOSSiBOT",
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.online

    @property
    def current_option(self) -> str | None:
        if not self.coordinator.data:
            return None
        raw = self.coordinator.data.get(TAG_LED_MODE)
        if raw is None:
            return None
        return _VALUE_TO_OPTION.get(raw)

    async def async_select_option(self, option: str) -> None:
        value = _OPTION_TO_VALUE[option]
        await self._api.async_send_control(
            self.coordinator.sn_code, TAG_LED_MODE, value
        )
        # Optimistic update - next WS frame (~1s) will confirm the real state.
        if self.coordinator.data is not None:
            new_data = dict(self.coordinator.data)
            new_data[TAG_LED_MODE] = value
            self.coordinator.async_set_updated_data(new_data)

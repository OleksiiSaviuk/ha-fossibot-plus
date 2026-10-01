"""Select entities (dropdowns) for the FOSSiBOT power station.

Covers LED mode and charge mode — both confirmed from captured
/ctrl/route requests with all CRC values verified.
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
from .const import DOMAIN, TAG_CHARGE_MODE, TAG_LED_MODE
from .coordinator import FossibotCoordinator

_LOGGER = logging.getLogger(__name__)

# --- LED mode ---------------------------------------------------------------
LED_OPTIONS = ["off", "steady", "sos", "strobe"]
LED_TO_VALUE = {"off": 0, "steady": 1, "sos": 2, "strobe": 3}
VALUE_TO_LED = {v: k for k, v in LED_TO_VALUE.items()}

# --- Charge mode ------------------------------------------------------------
CHARGE_OPTIONS = ["ups", "eco"]
CHARGE_TO_VALUE = {"ups": 0, "eco": 1}
VALUE_TO_CHARGE = {v: k for k, v in CHARGE_TO_VALUE.items()}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    api: FossibotApiClient = data["api"]
    entities = []
    for coordinator in data["coordinators"].values():
        entities.append(FossibotLedSelect(coordinator, api))
        entities.append(FossibotChargeModeSelect(coordinator, api))
    async_add_entities(entities)


class _FossibotSelect(CoordinatorEntity[FossibotCoordinator], SelectEntity):
    """Base class for FOSSiBOT select entities."""
    _attr_has_entity_name = True
    _tag: str
    _option_to_value: dict[str, int]
    _value_to_option: dict[int, str]

    def __init__(self, coordinator: FossibotCoordinator, api: FossibotApiClient) -> None:
        super().__init__(coordinator)
        self._api = api
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
        raw = self.coordinator.data.get(self._tag)
        return None if raw is None else self._value_to_option.get(raw)

    async def async_select_option(self, option: str) -> None:
        value = self._option_to_value[option]
        await self._api.async_send_control(self.coordinator.sn_code, self._tag, value)
        if self.coordinator.data is not None:
            new_data = dict(self.coordinator.data)
            new_data[self._tag] = value
            self.coordinator.async_set_updated_data(new_data)


class FossibotLedSelect(_FossibotSelect):
    _tag = TAG_LED_MODE
    _option_to_value = LED_TO_VALUE
    _value_to_option = VALUE_TO_LED
    _attr_options = LED_OPTIONS

    def __init__(self, coordinator: FossibotCoordinator, api: FossibotApiClient) -> None:
        super().__init__(coordinator, api)
        self.entity_description = SelectEntityDescription(
            key="led_mode", translation_key="led_mode", name="LED mode"
        )
        self._attr_unique_id = f"{coordinator.sn_code}_led_mode"


class FossibotChargeModeSelect(_FossibotSelect):
    _tag = TAG_CHARGE_MODE
    _option_to_value = CHARGE_TO_VALUE
    _value_to_option = VALUE_TO_CHARGE
    _attr_options = CHARGE_OPTIONS

    def __init__(self, coordinator: FossibotCoordinator, api: FossibotApiClient) -> None:
        super().__init__(coordinator, api)
        self.entity_description = SelectEntityDescription(
            key="charge_mode", translation_key="charge_mode", name="Charge mode"
        )
        self._attr_unique_id = f"{coordinator.sn_code}_charge_mode"

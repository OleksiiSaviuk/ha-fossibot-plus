"""Read-only boolean state (main power, AC output relay).

Actual control (switches) is a separate follow-up per the user's plan -
these are diagnostic/state read-back only.
"""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, TAG_AC_OUTPUT, TAG_POWER_STATE
from .coordinator import FossibotCoordinator

# (key, tag, translation_key)
BINARY_SENSOR_TYPES: tuple[tuple[str, str, str], ...] = (
    ("main_power", TAG_POWER_STATE, "main_power"),
    ("ac_output", TAG_AC_OUTPUT, "ac_output"),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    entities = [
        FossibotBinarySensor(coordinator, key, tag, translation_key)
        for coordinator in data["coordinators"].values()
        for key, tag, translation_key in BINARY_SENSOR_TYPES
    ]
    async_add_entities(entities)


class FossibotBinarySensor(CoordinatorEntity[FossibotCoordinator], BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.POWER

    def __init__(
        self,
        coordinator: FossibotCoordinator,
        key: str,
        tag: str,
        translation_key: str,
    ) -> None:
        super().__init__(coordinator)
        self._tag = tag
        self.entity_description = BinarySensorEntityDescription(
            key=key, translation_key=translation_key
        )
        self._attr_unique_id = f"{coordinator.sn_code}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.sn_code)},
            name=coordinator.device_name,
            manufacturer="FOSSiBOT",
        )

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None
        raw = self.coordinator.data.get(self._tag)
        return None if raw is None else bool(raw)

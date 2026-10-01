"""Diagnostic binary sensors for the FOSSiBOT power station.

Currently only exposes screen-timeout and power-off-timer as read-only
informational sensors (they are write-controlled via number entities if
added later). The output-memory and sound switches live in switch.py.
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

from .const import DOMAIN
from .coordinator import FossibotCoordinator

# No binary sensors enabled by default at this time — keeping the platform
# registered so future additions don't require a platform reload.
BINARY_SENSOR_TYPES: tuple[tuple[str, str, str, str], ...] = ()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    entities = [
        FossibotBinarySensor(coordinator, key, tag, translation_key, name)
        for coordinator in data["coordinators"].values()
        for key, tag, translation_key, name in BINARY_SENSOR_TYPES
    ]
    async_add_entities(entities)


class FossibotBinarySensor(CoordinatorEntity[FossibotCoordinator], BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.POWER
    _attr_entity_registry_enabled_default = False
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FossibotCoordinator,
        key: str,
        tag: str,
        translation_key: str,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._tag = tag
        self.entity_description = BinarySensorEntityDescription(
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

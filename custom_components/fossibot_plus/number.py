"""Number entity: AC charging power limit for the FOSSiBOT power station.

Tag 2a00 accepts raw watts directly (scale 1:1, step 100W).
Limits depend on the model selected during setup:
  F1800: 100–1200 W
  F3000: 100–2000 W

Confirmed from 6 captured ctrl commands (all CRC verified) and from
live WS telemetry where 2a00 changed in real time as commands were sent.
"""
from __future__ import annotations

import logging

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import FossibotApiClient
from .const import (
    CHARGE_POWER_LIMITS,
    CONF_MODEL,
    DOMAIN,
    MODEL_F1800,
    TAG_CHARGE_POWER,
)
from .coordinator import FossibotCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    api: FossibotApiClient = data["api"]
    # Options override initial data (allows changing model without re-adding)
    model = entry.options.get(CONF_MODEL) or entry.data.get(CONF_MODEL, MODEL_F1800)
    limits = CHARGE_POWER_LIMITS[model]

    entities = [
        FossibotChargePowerNumber(coordinator, api, limits)
        for coordinator in data["coordinators"].values()
    ]
    async_add_entities(entities)


class FossibotChargePowerNumber(CoordinatorEntity[FossibotCoordinator], NumberEntity):
    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX
    _attr_device_class = NumberDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(
        self,
        coordinator: FossibotCoordinator,
        api: FossibotApiClient,
        limits: dict,
    ) -> None:
        super().__init__(coordinator)
        self._api = api
        self.entity_description = NumberEntityDescription(
            key="charge_power_limit",
            translation_key="charge_power_limit",
            name="Charge power limit",
        )
        self._attr_unique_id = f"{coordinator.sn_code}_charge_power_limit"
        self._attr_native_min_value = limits["min"]
        self._attr_native_max_value = limits["max"]
        self._attr_native_step = limits["step"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.sn_code)},
            name=coordinator.device_name,
            manufacturer="FOSSiBOT",
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.online

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        raw = self.coordinator.data.get(TAG_CHARGE_POWER)
        return float(raw) if raw is not None else None

    async def async_set_native_value(self, value: float) -> None:
        watts = int(round(value / 100) * 100)  # snap to nearest 100W step
        watts = max(self._attr_native_min_value,
                    min(self._attr_native_max_value, watts))
        await self._api.async_send_control(
            self.coordinator.sn_code, TAG_CHARGE_POWER, watts
        )
        # Optimistic update
        if self.coordinator.data is not None:
            new_data = dict(self.coordinator.data)
            new_data[TAG_CHARGE_POWER] = watts
            self.coordinator.async_set_updated_data(new_data)

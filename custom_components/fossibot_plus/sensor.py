"""Sensor entities decoding FOSSiBOT TLV telemetry tags."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    TAG_AC_FREQUENCY,
    TAG_BATTERY_PACK,
    TAG_DC_OUTPUT,
    TAG_INPUT_POWER,
    TAG_INPUT_VOLTAGE,
    TAG_TEMP_BATTERY,
    TAG_TEMP_INVERTER,
    TAG_USB_OUTPUT,
)
from .coordinator import FossibotCoordinator


@dataclass(frozen=True, kw_only=True)
class FossibotSensorDescription(SensorEntityDescription):
    tag: str = ""
    scale: float = 1
    # None = whole 4-byte value; 0/1 = low/high 16-bit word of a tag that
    # actually packs two sub-values (see TAG_BATTERY_PACK in const.py).
    sub_word: int | None = None


SENSOR_TYPES: tuple[FossibotSensorDescription, ...] = (
    FossibotSensorDescription(
        key="input_power",
        tag=TAG_INPUT_POWER,
        translation_key="input_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="temp_inverter",
        tag=TAG_TEMP_INVERTER,
        translation_key="temp_inverter",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="temp_battery",
        tag=TAG_TEMP_BATTERY,
        translation_key="temp_battery",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="ac_frequency",
        tag=TAG_AC_FREQUENCY,
        translation_key="ac_frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
    ),
    # Disabled by default: the source spec never confirmed what these two
    # sub-values of tag 0x0500 actually represent (likely SOC / voltage,
    # but unverified against real hardware).
    FossibotSensorDescription(
        key="battery_pack_value_low",
        tag=TAG_BATTERY_PACK,
        sub_word=0,
        translation_key="battery_pack_value_low",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    FossibotSensorDescription(
        key="battery_pack_value_high",
        tag=TAG_BATTERY_PACK,
        sub_word=1,
        translation_key="battery_pack_value_high",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    FossibotSensorDescription(
        key="dc_output_mode",
        tag=TAG_DC_OUTPUT,
        translation_key="dc_output_mode",
    ),
    FossibotSensorDescription(
        key="usb_output_mode",
        tag=TAG_USB_OUTPUT,
        translation_key="usb_output_mode",
    ),
    # Source doc calls this "input voltage / current" for a single tag with
    # no scale factor given - can't be trusted yet, exposed raw & disabled.
    FossibotSensorDescription(
        key="input_voltage_or_current_raw",
        tag=TAG_INPUT_VOLTAGE,
        translation_key="input_voltage_or_current_raw",
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    entities = [
        FossibotSensor(coordinator, description)
        for coordinator in data["coordinators"].values()
        for description in SENSOR_TYPES
    ]
    async_add_entities(entities)


class FossibotSensor(CoordinatorEntity[FossibotCoordinator], SensorEntity):
    entity_description: FossibotSensorDescription

    def __init__(
        self, coordinator: FossibotCoordinator, description: FossibotSensorDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.sn_code}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.sn_code)},
            name=coordinator.device_name,
            manufacturer="FOSSiBOT",
        )

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        raw = self.coordinator.data.get(self.entity_description.tag)
        if raw is None:
            return None
        if self.entity_description.sub_word == 0:
            raw = raw & 0xFFFF
        elif self.entity_description.sub_word == 1:
            raw = (raw >> 16) & 0xFFFF
        return round(raw * self.entity_description.scale, 2)

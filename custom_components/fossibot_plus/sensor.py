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
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    TAG_AC_FREQUENCY,
    TAG_BATTERY_PACK,
    TAG_BATTERY_SOC,
    TAG_BATTERY_VOLTAGE_CANDIDATE,
    TAG_CHARGING_ACTIVE_CANDIDATE,
    TAG_INPUT_POWER_CANDIDATE,
    TAG_INPUT_POWER_MIRROR_CANDIDATE,
    TAG_INPUT_VOLTAGE,
    TAG_OUTPUT_POWER,
    TAG_OUTPUT_POWER_MIRROR,
    TAG_REMAINING_MINUTES,
    TAG_TEMPERATURE,
    TAG_UNKNOWN_2C00,
    TAG_UNKNOWN_2D00,
)
from .coordinator import FossibotCoordinator


@dataclass(frozen=True, kw_only=True)
class FossibotSensorDescription(SensorEntityDescription):
    tag: str = ""
    scale: float = 1


SENSOR_TYPES: tuple[FossibotSensorDescription, ...] = (
    # --- Confirmed against the real app screen (see DEVELOPMENT.md) -------
    FossibotSensorDescription(
        key="battery_soc",
        tag=TAG_BATTERY_SOC,
        name="Battery",
        translation_key="battery_soc",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="temperature",
        tag=TAG_TEMPERATURE,
        name="Temperature",
        translation_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="remaining_minutes",
        tag=TAG_REMAINING_MINUTES,
        name="Time remaining",
        translation_key="remaining_minutes",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="ac_frequency",
        tag=TAG_AC_FREQUENCY,
        name="AC frequency",
        translation_key="ac_frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
    ),
    FossibotSensorDescription(
        key="output_power",
        tag=TAG_OUTPUT_POWER,
        name="Output power",
        translation_key="output_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # --- Candidates (disabled by default) ---
    FossibotSensorDescription(
        key="output_power_mirror_raw",
        tag=TAG_OUTPUT_POWER_MIRROR,
        name="Output power mirror",
        translation_key="output_power_mirror_raw",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    FossibotSensorDescription(
        key="input_power_raw",
        tag=TAG_INPUT_POWER_CANDIDATE,
        name="Input power",
        translation_key="input_power_raw",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        scale=1,
        entity_registry_enabled_default=False,
    ),
    FossibotSensorDescription(
        key="input_power_mirror_raw",
        tag=TAG_INPUT_POWER_MIRROR_CANDIDATE,
        name="Input power mirror",
        translation_key="input_power_mirror_raw",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        scale=1,
        entity_registry_enabled_default=False,
    ),
    FossibotSensorDescription(
        key="charging_active_raw",
        tag=TAG_CHARGING_ACTIVE_CANDIDATE,
        name="Charging active",
        translation_key="charging_active_raw",
        entity_registry_enabled_default=False,
    ),
    FossibotSensorDescription(
        key="battery_voltage_raw",
        tag=TAG_BATTERY_VOLTAGE_CANDIDATE,
        name="Battery voltage",
        translation_key="battery_voltage_raw",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.01,
        entity_registry_enabled_default=False,
    ),
    # --- Unconfirmed (disabled by default) ---
    FossibotSensorDescription(
        key="input_voltage_or_current_raw",
        tag=TAG_INPUT_VOLTAGE,
        name="Input voltage or current",
        translation_key="input_voltage_or_current_raw",
        entity_registry_enabled_default=False,
    ),
    FossibotSensorDescription(
        key="unknown_2c00_raw",
        tag=TAG_UNKNOWN_2C00,
        name="Unknown 0x2c00",
        translation_key="unknown_2c00_raw",
        entity_registry_enabled_default=False,
    ),
    FossibotSensorDescription(
        key="unknown_2d00_raw",
        tag=TAG_UNKNOWN_2D00,
        name="Unknown 0x2d00",
        translation_key="unknown_2d00_raw",
        entity_registry_enabled_default=False,
    ),
    FossibotSensorDescription(
        key="battery_pack_raw",
        tag=TAG_BATTERY_PACK,
        name="Battery pack",
        translation_key="battery_pack_raw",
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
    _attr_has_entity_name = True

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
    def available(self) -> bool:
        return super().available and self.coordinator.online

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        raw = self.coordinator.data.get(self.entity_description.tag)
        if raw is None:
            return None
        return round(raw * self.entity_description.scale, 2)

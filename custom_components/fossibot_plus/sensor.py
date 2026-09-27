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
        translation_key="battery_soc",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="temperature",
        tag=TAG_TEMPERATURE,
        translation_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="remaining_minutes",
        tag=TAG_REMAINING_MINUTES,
        translation_key="remaining_minutes",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
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
    FossibotSensorDescription(
        key="output_power",
        tag=TAG_OUTPUT_POWER,
        translation_key="output_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # --- Candidates - plausible but not yet fully confirmed; disabled by
    # default until verified with more data --------------------------------
    # Identical to output_power in every frame observed so far. Kept
    # separate in case it diverges once DC/USB output alongside AC.
    FossibotSensorDescription(
        key="output_power_mirror_raw",
        tag=TAG_OUTPUT_POWER_MIRROR,
        translation_key="output_power_mirror_raw",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    # Direct watt value (scale 1:1). Confirmed by a stable AC-charging
    # session: 1300 ramped from ~262W at plug-in up to 398-402W at steady
    # state, matching the app's reported "~400W" input load exactly.
    # 1300 and 1400 (output power) are mutually exclusive - never both
    # nonzero at the same time - which makes sense: one is for charging,
    # one for discharging.
    FossibotSensorDescription(
        key="input_power_raw",
        tag=TAG_INPUT_POWER_CANDIDATE,
        translation_key="input_power_raw",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        scale=1,
        entity_registry_enabled_default=False,
    ),
    # Mirrors input_power_raw in every frame so far, same relationship as
    # the output_power/output_power_mirror_raw pair.
    FossibotSensorDescription(
        key="input_power_mirror_raw",
        tag=TAG_INPUT_POWER_MIRROR_CANDIDATE,
        translation_key="input_power_mirror_raw",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        scale=1,
        entity_registry_enabled_default=False,
    ),
    # 0 whenever idle, 1 throughout an active AC-charging capture - decent
    # correlation, but only two distinct states tested so far.
    FossibotSensorDescription(
        key="charging_active_raw",
        tag=TAG_CHARGING_ACTIVE_CANDIDATE,
        translation_key="charging_active_raw",
        entity_registry_enabled_default=False,
    ),
    # ~23.1V at 64-67% SOC while idle, but ~22.9-23.0V at 77% SOC while
    # charging - lower at a higher SOC is backwards for a simple resting
    # pack voltage, so treat this one with extra caution (see const.py).
    FossibotSensorDescription(
        key="battery_voltage_raw",
        tag=TAG_BATTERY_VOLTAGE_CANDIDATE,
        translation_key="battery_voltage_raw",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.01,
        entity_registry_enabled_default=False,
    ),
    # --- Unconfirmed / likely mislabeled - raw diagnostics, off by default -
    # Was constant 400 while idle, but dropped to 200 once AC charging
    # started - clearly charging-related, but exact meaning/scale unknown.
    FossibotSensorDescription(
        key="input_voltage_or_current_raw",
        tag=TAG_INPUT_VOLTAGE,
        translation_key="input_voltage_or_current_raw",
        entity_registry_enabled_default=False,
    ),
    # NOT the DC/USB on/off flags (those are confirmed elsewhere - see
    # switch.py); stayed at raw value 2 regardless of DC/USB state in every
    # capture. Likely unrelated (e.g. a port count or mode setting).
    FossibotSensorDescription(
        key="unknown_2c00_raw",
        tag=TAG_UNKNOWN_2C00,
        translation_key="unknown_2c00_raw",
        entity_registry_enabled_default=False,
    ),
    FossibotSensorDescription(
        key="unknown_2d00_raw",
        tag=TAG_UNKNOWN_2D00,
        translation_key="unknown_2d00_raw",
        entity_registry_enabled_default=False,
    ),
    # No established physical meaning - see const.py notes on TAG_BATTERY_PACK.
    FossibotSensorDescription(
        key="battery_pack_raw",
        tag=TAG_BATTERY_PACK,
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

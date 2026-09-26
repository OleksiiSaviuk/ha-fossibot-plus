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
    UnitOfFrequency,
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
    TAG_DC_OUTPUT,
    TAG_INPUT_VOLTAGE,
    TAG_REMAINING_MINUTES,
    TAG_TEMPERATURE,
    TAG_UNKNOWN_1400,
    TAG_UNKNOWN_2300,
    TAG_USB_OUTPUT,
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
    # --- Unconfirmed / likely mislabeled - raw diagnostics, off by default -
    # Value happened to equal the live output power (11 W) in the one
    # sample taken so far - could be power, could be a real temperature
    # that's coincidentally the same number. Needs a second, clearly
    # different power reading to tell apart.
    FossibotSensorDescription(
        key="unknown_1400_raw",
        tag=TAG_UNKNOWN_1400,
        translation_key="unknown_1400_raw",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    FossibotSensorDescription(
        key="unknown_2300_raw",
        tag=TAG_UNKNOWN_2300,
        translation_key="unknown_2300_raw",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    # Stayed constant regardless of the DC/USB toggle state in the app -
    # likely a static value (e.g. a port count), not live on/off state.
    FossibotSensorDescription(
        key="dc_output_raw",
        tag=TAG_DC_OUTPUT,
        translation_key="dc_output_raw",
        entity_registry_enabled_default=False,
    ),
    FossibotSensorDescription(
        key="usb_output_raw",
        tag=TAG_USB_OUTPUT,
        translation_key="usb_output_raw",
        entity_registry_enabled_default=False,
    ),
    # Stayed constant (400) across two captures with very different power
    # states - likely a static/rated spec value, not a live measurement.
    FossibotSensorDescription(
        key="input_voltage_or_current_raw",
        tag=TAG_INPUT_VOLTAGE,
        translation_key="input_voltage_or_current_raw",
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
    def native_value(self):
        if not self.coordinator.data:
            return None
        raw = self.coordinator.data.get(self.entity_description.tag)
        if raw is None:
            return None
        return round(raw * self.entity_description.scale, 2)

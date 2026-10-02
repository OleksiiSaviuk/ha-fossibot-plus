"""Sensor entities decoding FOSSiBOT TLV telemetry tags."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

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
    TAG_AC_GRID_POWER,
    TAG_AC_OUTPUT_POWER,
    TAG_AC_OUTPUT_VOLTAGE,
    TAG_BATTERY_SOC,
    TAG_CHARGE_POWER,
    TAG_CHARGING_ACTIVE,
    TAG_REMAINING_MINUTES,
    TAG_TEMPERATURE,
    TAG_TOTAL_INPUT_POWER,
    TAG_TOTAL_OUTPUT_POWER,
    TAG_USB_OUTPUT_POWER,
)
from .coordinator import FossibotCoordinator


@dataclass(frozen=True, kw_only=True)
class FossibotSensorDescription(SensorEntityDescription):
    tag: str = ""
    scale: float = 1
    # Optional post-processing (e.g. take only low 16 bits)
    raw_transform: Callable[[int], int] | None = None


def _low16(v: int) -> int:
    """Return only the lower 16 bits — handles models that pack metadata in high word."""
    return v & 0xFFFF


SENSOR_TYPES: tuple[FossibotSensorDescription, ...] = (
    # ✅ Confirmed ─────────────────────────────────────────────────────────────
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
        # Some models pack extra data in the high 16 bits of this tag (e.g.
        # one device reported raw=196638 = 0x0003001E; low16=30°C is correct).
        # Taking only the low 16 bits is safe for all observed models.
        raw_transform=_low16,
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
        key="charging",
        tag=TAG_CHARGING_ACTIVE,
        name="Charging",
        translation_key="charging",
    ),
    # ✅ Output power breakdown (confirmed: 2300 = 1400 + 2500 in every frame)
    FossibotSensorDescription(
        key="ac_output_power",
        tag=TAG_AC_OUTPUT_POWER,
        name="AC output power",
        translation_key="ac_output_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="usb_output_power",
        tag=TAG_USB_OUTPUT_POWER,
        name="USB output power",
        translation_key="usb_output_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="total_output_power",
        tag=TAG_TOTAL_OUTPUT_POWER,
        name="Total output power",
        translation_key="total_output_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="ac_output_voltage",
        tag=TAG_AC_OUTPUT_VOLTAGE,
        name="AC output voltage",
        translation_key="ac_output_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        scale=0.1,
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
    # ✅ Input / charging power
    FossibotSensorDescription(
        key="ac_grid_power",
        tag=TAG_AC_GRID_POWER,
        name="AC grid power",
        translation_key="ac_grid_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="total_input_power",
        tag=TAG_TOTAL_INPUT_POWER,
        name="Total input power",
        translation_key="total_input_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    FossibotSensorDescription(
        key="charge_power",
        tag=TAG_CHARGE_POWER,
        name="Charge power",
        translation_key="charge_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
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
        if self.entity_description.raw_transform is not None:
            raw = self.entity_description.raw_transform(raw)
        return round(raw * self.entity_description.scale, 2)

"""Sensors for the JUDO ZEWA i-SAFE integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import AbsencePeriod
from .const import DOMAIN
from .coordinator import JudoZewaDataUpdateCoordinator
from .entity import JudoZewaEntity


@dataclass(frozen=True, kw_only=True)
class JudoZewaSensorDescription(SensorEntityDescription):
    """Describe a JUDO sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


SENSOR_DESCRIPTIONS: tuple[JudoZewaSensorDescription, ...] = (
    JudoZewaSensorDescription(
        key="total_water_m3",
        translation_key="total_water_m3",
        native_unit_of_measurement="m³",
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.get("total_water_m3"),
    ),
    JudoZewaSensorDescription(
        key="absence_flow_l_h",
        translation_key="absence_flow_l_h",
        native_unit_of_measurement="L/h",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("absence_flow_l_h"),
    ),
    JudoZewaSensorDescription(
        key="absence_volume_l",
        translation_key="absence_volume_l",
        native_unit_of_measurement="L",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("absence_volume_l"),
    ),
    JudoZewaSensorDescription(
        key="absence_duration_min",
        translation_key="absence_duration_min",
        native_unit_of_measurement="min",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("absence_duration_min"),
    ),
    JudoZewaSensorDescription(
        key="sleep_duration_hours",
        translation_key="sleep_duration_hours",
        native_unit_of_measurement="h",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("sleep_duration_hours"),
    ),
    JudoZewaSensorDescription(
        key="learning_remaining_m3",
        translation_key="learning_remaining_m3",
        native_unit_of_measurement="m³",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("learning_remaining_m3"),
    ),
    JudoZewaSensorDescription(
        key="device_datetime",
        translation_key="device_datetime",
        value_fn=lambda data: _format_device_datetime(data.get("device_datetime")),
    ),
    JudoZewaSensorDescription(
        key="install_date",
        translation_key="install_date",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.get("install_date"),
    ),
    JudoZewaSensorDescription(
        key="device_type_name",
        translation_key="device_type_name",
        value_fn=lambda data: data.get("device_type_name"),
    ),
    JudoZewaSensorDescription(
        key="serial_number",
        translation_key="serial_number",
        value_fn=lambda data: data.get("serial_number"),
    ),
    JudoZewaSensorDescription(
        key="sw_version",
        translation_key="sw_version",
        value_fn=lambda data: data.get("sw_version"),
    ),
)

ABSENCE_PERIOD_DESCRIPTIONS: tuple[JudoZewaSensorDescription, ...] = tuple(
    JudoZewaSensorDescription(
        key=f"absence_period_{index}",
        translation_key=f"absence_period_{index}",
        value_fn=lambda data, index=index: _absence_period_state(data, index),
    )
    for index in range(7)
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up JUDO ZEWA sensors."""
    coordinator: JudoZewaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        JudoZewaSensor(coordinator, description) for description in (*SENSOR_DESCRIPTIONS, *ABSENCE_PERIOD_DESCRIPTIONS)
    )


class JudoZewaSensor(JudoZewaEntity, SensorEntity):
    """Representation of a JUDO ZEWA sensor."""

    entity_description: JudoZewaSensorDescription

    def __init__(self, coordinator: JudoZewaDataUpdateCoordinator, description: JudoZewaSensorDescription) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return attributes for absence-period sensors."""
        if not self.entity_description.key.startswith("absence_period_"):
            return None
        try:
            index = int(self.entity_description.key.rsplit("_", 1)[1])
        except ValueError:
            return None
        period = (self.coordinator.data or {}).get("absence_periods", {}).get(index)
        if isinstance(period, AbsencePeriod):
            return period.as_dict()
        return None


def _format_device_datetime(value: Any) -> str | None:
    """Format a device-local datetime for display."""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return None


def _absence_period_state(data: dict[str, Any], index: int) -> str | None:
    """Return a sensor state for one absence period."""
    period = data.get("absence_periods", {}).get(index)
    if isinstance(period, AbsencePeriod):
        return period.state
    return None

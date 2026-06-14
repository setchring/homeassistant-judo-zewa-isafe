"""Number entities for the JUDO ZEWA i-SAFE integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import JudoZewaDataUpdateCoordinator
from .entity import JudoZewaEntity


@dataclass(frozen=True, kw_only=True)
class JudoZewaNumberDescription(NumberEntityDescription):
    """Describe a writable number entity."""

    value_fn: Callable[[dict[str, Any]], float | int | None]
    setter: str


NUMBER_DESCRIPTIONS: tuple[JudoZewaNumberDescription, ...] = (
    JudoZewaNumberDescription(
        key="absence_flow_l_h",
        translation_key="absence_flow_l_h",
        native_min_value=0,
        native_max_value=65535,
        native_step=1,
        native_unit_of_measurement="L/h",
        setter="absence_flow_l_h",
        value_fn=lambda data: data.get("absence_flow_l_h"),
    ),
    JudoZewaNumberDescription(
        key="absence_volume_l",
        translation_key="absence_volume_l",
        native_min_value=0,
        native_max_value=65535,
        native_step=1,
        native_unit_of_measurement="L",
        setter="absence_volume_l",
        value_fn=lambda data: data.get("absence_volume_l"),
    ),
    JudoZewaNumberDescription(
        key="absence_duration_min",
        translation_key="absence_duration_min",
        native_min_value=0,
        native_max_value=65535,
        native_step=1,
        native_unit_of_measurement="min",
        setter="absence_duration_min",
        value_fn=lambda data: data.get("absence_duration_min"),
    ),
    JudoZewaNumberDescription(
        key="sleep_duration_hours",
        translation_key="sleep_duration_hours",
        native_min_value=1,
        native_max_value=10,
        native_step=1,
        native_unit_of_measurement="h",
        setter="sleep_duration_hours",
        value_fn=lambda data: data.get("sleep_duration_hours"),
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up JUDO ZEWA number entities."""
    coordinator: JudoZewaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(JudoZewaNumber(coordinator, description) for description in NUMBER_DESCRIPTIONS)


class JudoZewaNumber(JudoZewaEntity, NumberEntity):
    """Representation of a JUDO ZEWA writable number."""

    entity_description: JudoZewaNumberDescription

    def __init__(self, coordinator: JudoZewaDataUpdateCoordinator, description: JudoZewaNumberDescription) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | None:
        """Return the current number value."""
        return self.entity_description.value_fn(self.coordinator.data or {})

    async def async_set_native_value(self, value: float) -> None:
        """Write a value to the device."""
        key = self.entity_description.setter
        data = dict(self.coordinator.data or {})

        if key == "sleep_duration_hours":
            await self.coordinator.api.async_set_sleep_duration_hours(int(value))
        else:
            data[key] = int(value)
            await self.coordinator.api.async_set_absence_limits(
                int(data.get("absence_flow_l_h") or 0),
                int(data.get("absence_volume_l") or 0),
                int(data.get("absence_duration_min") or 0),
            )

        await self.coordinator.async_request_refresh()

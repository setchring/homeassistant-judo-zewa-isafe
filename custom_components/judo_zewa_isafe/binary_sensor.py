"""Binary sensors for the JUDO ZEWA i-SAFE integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import JudoZewaDataUpdateCoordinator
from .entity import JudoZewaEntity


@dataclass(frozen=True, kw_only=True)
class JudoZewaBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a JUDO binary sensor."""

    value_fn: Callable[[dict[str, Any]], bool | None]


BINARY_SENSOR_DESCRIPTIONS: tuple[JudoZewaBinarySensorDescription, ...] = (
    JudoZewaBinarySensorDescription(
        key="learning_active",
        translation_key="learning_active",
        value_fn=lambda data: data.get("learning_active"),
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up JUDO ZEWA binary sensors."""
    coordinator: JudoZewaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(JudoZewaBinarySensor(coordinator, description) for description in BINARY_SENSOR_DESCRIPTIONS)


class JudoZewaBinarySensor(JudoZewaEntity, BinarySensorEntity):
    """Representation of a JUDO ZEWA binary sensor."""

    entity_description: JudoZewaBinarySensorDescription

    def __init__(
        self,
        coordinator: JudoZewaDataUpdateCoordinator,
        description: JudoZewaBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.entity_description.value_fn(self.coordinator.data or {})

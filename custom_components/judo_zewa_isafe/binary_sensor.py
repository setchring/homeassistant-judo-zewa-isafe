"""Binary sensors for the JUDO ZEWA i-SAFE integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_CLOUD_ENABLED, DEFAULT_CLOUD_ENABLED, DOMAIN
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
    JudoZewaBinarySensorDescription(
        key="valve_open",
        translation_key="valve_open",
        device_class=BinarySensorDeviceClass.OPENING,
        value_fn=lambda data: data.get("valve_open"),
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up JUDO ZEWA binary sensors."""
    coordinator: JudoZewaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    config = {**entry.data, **entry.options}
    descriptions = [
        description
        for description in BINARY_SENSOR_DESCRIPTIONS
        if description.key != "valve_open" or config.get(CONF_CLOUD_ENABLED, DEFAULT_CLOUD_ENABLED)
    ]
    async_add_entities(JudoZewaBinarySensor(coordinator, description) for description in descriptions)


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

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return diagnostic attributes for the cloud valve sensor."""
        if self.entity_description.key != "valve_open":
            return None
        data = self.coordinator.data or {}
        return {
            "source": "JU-Control Cloud",
            "device_status": data.get("valve_cloud_device_status"),
            "last_cloud_update": data.get("valve_cloud_last_update"),
            "cloud_updated_at": data.get("valve_cloud_updated_at"),
            "status_byte_23": data.get("valve_cloud_status_byte_23"),
            "status_block_150": data.get("valve_cloud_status_block_150"),
            "cloud_error": data.get("valve_cloud_error"),
        }

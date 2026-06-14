"""Shared entity helpers for the JUDO ZEWA i-SAFE integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME
from .coordinator import JudoZewaDataUpdateCoordinator


class JudoZewaEntity(CoordinatorEntity[JudoZewaDataUpdateCoordinator]):
    """Base class for JUDO ZEWA entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: JudoZewaDataUpdateCoordinator, key: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        serial = coordinator.data.get("serial_number") if coordinator.data else None
        identifier = serial or coordinator.api.host
        self._attr_unique_id = f"{identifier}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device information."""
        data = self.coordinator.data or {}
        serial = data.get("serial_number") or self.coordinator.api.host
        return DeviceInfo(
            identifiers={(DOMAIN, str(serial))},
            manufacturer="JUDO",
            name=NAME,
            model=data.get("device_type_name") or "ZEWA i-SAFE",
            serial_number=data.get("serial_number"),
            sw_version=data.get("sw_version"),
        )

"""Select entities for the JUDO ZEWA i-SAFE integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import JudoZewaDataUpdateCoordinator
from .entity import JudoZewaEntity

MICROLEAKAGE_OPTIONS: dict[int, str] = {
    0: "Keine automatische Prüfung",
    1: "Prüfung mit Meldung",
    2: "Prüfung mit Meldung und Schließen",
}
MICROLEAKAGE_OPTIONS_REVERSE = {label: value for value, label in MICROLEAKAGE_OPTIONS.items()}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up JUDO ZEWA select entities."""
    coordinator: JudoZewaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([JudoZewaMicroleakageSelect(coordinator)])


class JudoZewaMicroleakageSelect(JudoZewaEntity, SelectEntity):
    """Select the automatic micro-leakage-test mode."""

    _attr_translation_key = "microleakage_mode"
    _attr_options = list(MICROLEAKAGE_OPTIONS.values())

    def __init__(self, coordinator: JudoZewaDataUpdateCoordinator) -> None:
        """Initialize the select."""
        super().__init__(coordinator, "microleakage_mode")

    @property
    def current_option(self) -> str | None:
        """Return the selected option."""
        mode = (self.coordinator.data or {}).get("microleakage_mode")
        return MICROLEAKAGE_OPTIONS.get(mode)

    async def async_select_option(self, option: str) -> None:
        """Write the selected option to the device."""
        await self.coordinator.api.async_set_microleakage_mode(MICROLEAKAGE_OPTIONS_REVERSE[option])
        await self.coordinator.async_request_refresh()

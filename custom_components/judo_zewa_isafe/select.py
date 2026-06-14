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

VACATION_MODE_TYPE_OPTIONS: dict[int, str] = {
    0: "Aus",
    1: "U1",
    2: "U2",
    3: "U3",
}
VACATION_MODE_TYPE_OPTIONS_REVERSE = {label: value for value, label in VACATION_MODE_TYPE_OPTIONS.items()}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up JUDO ZEWA select entities."""
    coordinator: JudoZewaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            JudoZewaMicroleakageSelect(coordinator),
            JudoZewaVacationModeTypeSelect(coordinator),
        ]
    )


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


class JudoZewaVacationModeTypeSelect(JudoZewaEntity, SelectEntity):
    """Select the vacation-mode type.

    The JUDO API documents only a write command for this value. Therefore the
    entity shows an optimistic value after it has been set through Home Assistant
    and otherwise remains unknown after restart.
    """

    _attr_translation_key = "vacation_mode_type"
    _attr_options = list(VACATION_MODE_TYPE_OPTIONS.values())

    def __init__(self, coordinator: JudoZewaDataUpdateCoordinator) -> None:
        """Initialize the select."""
        super().__init__(coordinator, "vacation_mode_type")
        self._current_option: str | None = None

    @property
    def current_option(self) -> str | None:
        """Return the selected option."""
        return self._current_option

    async def async_select_option(self, option: str) -> None:
        """Write the selected option to the device."""
        await self.coordinator.api.async_set_vacation_mode_type(VACATION_MODE_TYPE_OPTIONS_REVERSE[option])
        self._current_option = option
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

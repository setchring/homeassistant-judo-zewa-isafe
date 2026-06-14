"""Buttons for the JUDO ZEWA i-SAFE integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import JudoZewaDataUpdateCoordinator
from .entity import JudoZewaEntity


@dataclass(frozen=True, kw_only=True)
class JudoZewaButtonDescription(ButtonEntityDescription):
    """Describe a JUDO command button."""

    command: str


BUTTON_DESCRIPTIONS: tuple[JudoZewaButtonDescription, ...] = (
    JudoZewaButtonDescription(key="reset_message", translation_key="reset_message", command="6300"),
    JudoZewaButtonDescription(key="close_leakage_protection", translation_key="close_leakage_protection", command="5100"),
    JudoZewaButtonDescription(key="open_leakage_protection", translation_key="open_leakage_protection", command="5200"),
    JudoZewaButtonDescription(key="start_sleep_mode", translation_key="start_sleep_mode", command="5400"),
    JudoZewaButtonDescription(key="stop_sleep_mode", translation_key="stop_sleep_mode", command="5500"),
    JudoZewaButtonDescription(key="start_vacation_mode", translation_key="start_vacation_mode", command="5700"),
    JudoZewaButtonDescription(key="stop_vacation_mode", translation_key="stop_vacation_mode", command="5800"),
    JudoZewaButtonDescription(key="start_microleakage_test", translation_key="start_microleakage_test", command="5C00"),
    JudoZewaButtonDescription(key="start_learning_mode", translation_key="start_learning_mode", command="5D00"),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up JUDO ZEWA buttons."""
    coordinator: JudoZewaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(JudoZewaButton(coordinator, description) for description in BUTTON_DESCRIPTIONS)


class JudoZewaButton(JudoZewaEntity, ButtonEntity):
    """Representation of a JUDO command button."""

    entity_description: JudoZewaButtonDescription

    def __init__(self, coordinator: JudoZewaDataUpdateCoordinator, description: JudoZewaButtonDescription) -> None:
        """Initialize the button."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.api.async_press_button(self.entity_description.command)
        await self.coordinator.async_request_refresh()

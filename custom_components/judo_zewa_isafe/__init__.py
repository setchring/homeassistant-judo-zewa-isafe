"""JUDO ZEWA i-SAFE integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import JudoZewaApi
from .const import DEFAULT_PASSWORD, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DEFAULT_USERNAME, DOMAIN, PLATFORMS
from .coordinator import JudoZewaDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up JUDO ZEWA i-SAFE from a config entry."""
    session = async_get_clientsession(hass)
    api = JudoZewaApi(
        session=session,
        host=entry.data[CONF_HOST],
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
        username=entry.data.get(CONF_USERNAME, DEFAULT_USERNAME),
        password=entry.data.get(CONF_PASSWORD, DEFAULT_PASSWORD),
    )
    coordinator = JudoZewaDataUpdateCoordinator(
        hass=hass,
        api=api,
        scan_interval=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

"""JUDO ZEWA i-SAFE integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import JudoZewaApi
from .cloud_api import JudoJuControlCloudApi
from .const import (
    CONF_CLOUD_DEVICE,
    CONF_CLOUD_ENABLED,
    CONF_CLOUD_PASSWORD,
    CONF_CLOUD_USERNAME,
    DEFAULT_CLOUD_ENABLED,
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import JudoZewaDataUpdateCoordinator

SERVICES_REGISTERED = "services_registered"


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
    config = {**entry.data, **entry.options}
    cloud_api = None
    if config.get(CONF_CLOUD_ENABLED, DEFAULT_CLOUD_ENABLED):
        cloud_api = JudoJuControlCloudApi(
            session=session,
            username=config.get(CONF_CLOUD_USERNAME, ""),
            password=config.get(CONF_CLOUD_PASSWORD, ""),
            device_hint=config.get(CONF_CLOUD_DEVICE),
        )

    coordinator = JudoZewaDataUpdateCoordinator(
        hass=hass,
        api=api,
        scan_interval=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        cloud_api=cloud_api,
    )
    await coordinator.async_config_entry_first_refresh()

    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data[entry.entry_id] = coordinator
    if not domain_data.get(SERVICES_REGISTERED):
        # Import lazily so config_flow loading is not blocked by optional
        # service-response APIs that differ between Home Assistant versions.
        from .services import async_setup_services

        async_setup_services(hass)
        domain_data[SERVICES_REGISTERED] = True

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        domain_data = hass.data[DOMAIN]
        domain_data.pop(entry.entry_id)
        configured_entries = [key for key in domain_data if key != SERVICES_REGISTERED]
        if not configured_entries:
            from .services import async_unload_services

            async_unload_services(hass)
            hass.data.pop(DOMAIN)
    return unload_ok

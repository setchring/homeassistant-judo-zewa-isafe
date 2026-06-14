"""Config flow for the JUDO ZEWA i-SAFE integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CannotConnect, InvalidAuth, JudoZewaApi, UnsupportedDevice
from .const import (
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)
        ),
    }
)


async def _validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str | None]:
    """Validate user input against the physical device."""
    api = JudoZewaApi(
        session=async_get_clientsession(hass),
        host=data[CONF_HOST],
        port=data[CONF_PORT],
        username=data.get(CONF_USERNAME),
        password=data.get(CONF_PASSWORD),
    )
    identity = await api.async_validate()
    title = "JUDO ZEWA i-SAFE"
    if identity.serial_number:
        title = f"JUDO ZEWA i-SAFE {identity.serial_number}"
    return {
        "title": title,
        "unique_id": identity.serial_number or data[CONF_HOST],
    }


class JudoZewaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for JUDO ZEWA i-SAFE."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await _validate_input(self.hass, user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except UnsupportedDevice:
                errors["base"] = "unsupported_device"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - surfaced as generic form error
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(str(info["unique_id"]))
                self._abort_if_unique_id_configured(updates={CONF_HOST: user_input[CONF_HOST]})
                return self.async_create_entry(title=str(info["title"]), data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

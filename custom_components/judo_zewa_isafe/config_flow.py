"""Config flow for the JUDO ZEWA i-SAFE integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CannotConnect, InvalidAuth, JudoZewaApi, UnsupportedDevice
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
        vol.Optional(CONF_CLOUD_ENABLED, default=DEFAULT_CLOUD_ENABLED): bool,
        vol.Optional(CONF_CLOUD_USERNAME): str,
        vol.Optional(CONF_CLOUD_PASSWORD): str,
        vol.Optional(CONF_CLOUD_DEVICE): str,
    }
)


def _cloud_options_schema(entry: config_entries.ConfigEntry) -> vol.Schema:
    """Return the options form schema."""
    config = {**entry.data, **entry.options}
    return vol.Schema(
        {
            vol.Optional(CONF_CLOUD_ENABLED, default=config.get(CONF_CLOUD_ENABLED, DEFAULT_CLOUD_ENABLED)): bool,
            vol.Optional(CONF_CLOUD_USERNAME, default=config.get(CONF_CLOUD_USERNAME, "")): str,
            vol.Optional(CONF_CLOUD_PASSWORD, default=config.get(CONF_CLOUD_PASSWORD, "")): str,
            vol.Optional(CONF_CLOUD_DEVICE, default=config.get(CONF_CLOUD_DEVICE, "")): str,
        }
    )


async def _validate_cloud_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate optional JU-Control cloud access."""
    if not data.get(CONF_CLOUD_ENABLED, DEFAULT_CLOUD_ENABLED):
        return

    if not data.get(CONF_CLOUD_USERNAME) or not data.get(CONF_CLOUD_PASSWORD):
        raise InvalidAuth("JU-Control username and password are required")

    cloud_api = JudoJuControlCloudApi(
        session=async_get_clientsession(hass),
        username=data[CONF_CLOUD_USERNAME],
        password=data[CONF_CLOUD_PASSWORD],
        device_hint=data.get(CONF_CLOUD_DEVICE),
    )
    await cloud_api.async_validate()


async def _validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str | None]:
    """Validate user input against the physical device and optional cloud."""
    api = JudoZewaApi(
        session=async_get_clientsession(hass),
        host=data[CONF_HOST],
        port=data[CONF_PORT],
        username=data.get(CONF_USERNAME),
        password=data.get(CONF_PASSWORD),
    )
    identity = await api.async_validate()
    await _validate_cloud_input(hass, data)
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

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "JudoZewaOptionsFlow":
        """Return the options flow."""
        return JudoZewaOptionsFlow(config_entry)

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


class JudoZewaOptionsFlow(config_entries.OptionsFlow):
    """Handle JUDO ZEWA options."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        """Initialize the options flow."""
        self._entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage JU-Control cloud options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            merged = {**self._entry.data, **user_input}
            try:
                await _validate_cloud_input(self.hass, merged)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - surfaced as generic form error
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_cloud_options_schema(self._entry),
            errors=errors,
        )

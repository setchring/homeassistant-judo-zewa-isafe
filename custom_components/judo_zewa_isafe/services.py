"""Domain services for the JUDO ZEWA i-SAFE integration."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
import homeassistant.util.dt as dt_util

try:
    from homeassistant.core import SupportsResponse
except ImportError:  # Home Assistant versions before service responses
    SupportsResponse = None  # type: ignore[assignment]

from .const import DOMAIN
from .coordinator import JudoZewaDataUpdateCoordinator

SERVICE_SET_LEAKAGE_SETTINGS = "set_leakage_settings"
SERVICE_SET_VACATION_MODE_TYPE = "set_vacation_mode_type"
SERVICE_GET_DEVICE_DATETIME = "get_device_datetime"
SERVICE_SET_DEVICE_DATETIME = "set_device_datetime"
SERVICE_SYNC_DEVICE_DATETIME = "sync_device_datetime"
SERVICE_GET_ABSENCE_PERIOD = "get_absence_period"
SERVICE_SET_ABSENCE_PERIOD = "set_absence_period"
SERVICE_DELETE_ABSENCE_PERIOD = "delete_absence_period"
SERVICE_GET_DAY_STATISTICS = "get_day_statistics"
SERVICE_GET_WEEK_STATISTICS = "get_week_statistics"
SERVICE_GET_MONTH_STATISTICS = "get_month_statistics"
SERVICE_GET_YEAR_STATISTICS = "get_year_statistics"

ATTR_VACATION_MODE_TYPE = "vacation_mode_type"
ATTR_FLOW_L_H = "flow_l_h"
ATTR_VOLUME_L = "volume_l"
ATTR_DURATION_MIN = "duration_min"
ATTR_DATETIME = "datetime"
ATTR_INDEX = "index"
ATTR_START_DAY = "start_day"
ATTR_START_HOUR = "start_hour"
ATTR_START_MINUTE = "start_minute"
ATTR_STOP_DAY = "stop_day"
ATTR_STOP_HOUR = "stop_hour"
ATTR_STOP_MINUTE = "stop_minute"
ATTR_DATE = "date"
ATTR_YEAR = "year"
ATTR_MONTH = "month"
ATTR_CALENDAR_WEEK = "calendar_week"

CONF_CONFIG_ENTRY_ID = "config_entry_id"
CONFIG_ENTRY_FIELD = vol.Optional(CONF_CONFIG_ENTRY_ID)


def _response_kwargs() -> dict[str, Any]:
    """Return async_register kwargs for response services when supported."""
    if SupportsResponse is None:
        return {}
    return {"supports_response": SupportsResponse.ONLY}



def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration-level services."""

    async def handle_set_leakage_settings(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        await coordinator.api.async_set_leakage_settings(
            int(call.data[ATTR_VACATION_MODE_TYPE]),
            int(call.data[ATTR_FLOW_L_H]),
            int(call.data[ATTR_VOLUME_L]),
            int(call.data[ATTR_DURATION_MIN]),
        )
        await coordinator.async_request_refresh()

    async def handle_set_vacation_mode_type(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        await coordinator.api.async_set_vacation_mode_type(int(call.data[ATTR_VACATION_MODE_TYPE]))
        await coordinator.async_request_refresh()

    async def handle_get_device_datetime(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator_from_call(hass, call)
        value = await coordinator.api.async_read_device_datetime()
        return {"datetime": value.isoformat(sep=" ") if value else None}

    async def handle_set_device_datetime(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        value = _parse_datetime(call.data[ATTR_DATETIME])
        await coordinator.api.async_set_device_datetime(value)
        await coordinator.async_request_refresh()

    async def handle_sync_device_datetime(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        await coordinator.api.async_set_device_datetime(dt_util.now().replace(tzinfo=None))
        await coordinator.async_request_refresh()

    async def handle_get_absence_period(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator_from_call(hass, call)
        period = await coordinator.api.async_read_absence_period(int(call.data[ATTR_INDEX]))
        return period.as_dict()

    async def handle_set_absence_period(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        await coordinator.api.async_set_absence_period(
            int(call.data[ATTR_INDEX]),
            int(call.data[ATTR_START_DAY]),
            int(call.data[ATTR_START_HOUR]),
            int(call.data[ATTR_START_MINUTE]),
            int(call.data[ATTR_STOP_DAY]),
            int(call.data[ATTR_STOP_HOUR]),
            int(call.data[ATTR_STOP_MINUTE]),
        )
        await coordinator.async_request_refresh()

    async def handle_delete_absence_period(call: ServiceCall) -> None:
        coordinator = _coordinator_from_call(hass, call)
        await coordinator.api.async_delete_absence_period(int(call.data[ATTR_INDEX]))
        await coordinator.async_request_refresh()

    async def handle_get_day_statistics(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator_from_call(hass, call)
        statistic_date = _parse_date(call.data[ATTR_DATE])
        return await coordinator.api.async_read_day_statistics(statistic_date)

    async def handle_get_week_statistics(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator_from_call(hass, call)
        return await coordinator.api.async_read_week_statistics(
            int(call.data[ATTR_YEAR]),
            int(call.data[ATTR_CALENDAR_WEEK]),
        )

    async def handle_get_month_statistics(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator_from_call(hass, call)
        return await coordinator.api.async_read_month_statistics(int(call.data[ATTR_YEAR]), int(call.data[ATTR_MONTH]))

    async def handle_get_year_statistics(call: ServiceCall) -> dict[str, Any]:
        coordinator = _coordinator_from_call(hass, call)
        return await coordinator.api.async_read_year_statistics(int(call.data[ATTR_YEAR]))

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_LEAKAGE_SETTINGS,
        handle_set_leakage_settings,
        schema=vol.Schema(
            {
                CONFIG_ENTRY_FIELD: str,
                vol.Required(ATTR_VACATION_MODE_TYPE): vol.All(vol.Coerce(int), vol.Range(min=0, max=3)),
                vol.Required(ATTR_FLOW_L_H): vol.All(vol.Coerce(int), vol.Range(min=0, max=65535)),
                vol.Required(ATTR_VOLUME_L): vol.All(vol.Coerce(int), vol.Range(min=0, max=65535)),
                vol.Required(ATTR_DURATION_MIN): vol.All(vol.Coerce(int), vol.Range(min=0, max=65535)),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_VACATION_MODE_TYPE,
        handle_set_vacation_mode_type,
        schema=vol.Schema(
            {
                CONFIG_ENTRY_FIELD: str,
                vol.Required(ATTR_VACATION_MODE_TYPE): vol.All(vol.Coerce(int), vol.Range(min=0, max=3)),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_DEVICE_DATETIME,
        handle_get_device_datetime,
        schema=vol.Schema({CONFIG_ENTRY_FIELD: str}),
        **_response_kwargs(),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_DEVICE_DATETIME,
        handle_set_device_datetime,
        schema=vol.Schema({CONFIG_ENTRY_FIELD: str, vol.Required(ATTR_DATETIME): str}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SYNC_DEVICE_DATETIME,
        handle_sync_device_datetime,
        schema=vol.Schema({CONFIG_ENTRY_FIELD: str}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_ABSENCE_PERIOD,
        handle_get_absence_period,
        schema=vol.Schema(
            {CONFIG_ENTRY_FIELD: str, vol.Required(ATTR_INDEX): vol.All(vol.Coerce(int), vol.Range(min=0, max=6))}
        ),
        **_response_kwargs(),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ABSENCE_PERIOD,
        handle_set_absence_period,
        schema=vol.Schema(
            {
                CONFIG_ENTRY_FIELD: str,
                vol.Required(ATTR_INDEX): vol.All(vol.Coerce(int), vol.Range(min=0, max=6)),
                vol.Required(ATTR_START_DAY): vol.All(vol.Coerce(int), vol.Range(min=0, max=6)),
                vol.Required(ATTR_START_HOUR): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
                vol.Required(ATTR_START_MINUTE): vol.All(vol.Coerce(int), vol.Range(min=0, max=59)),
                vol.Required(ATTR_STOP_DAY): vol.All(vol.Coerce(int), vol.Range(min=0, max=6)),
                vol.Required(ATTR_STOP_HOUR): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
                vol.Required(ATTR_STOP_MINUTE): vol.All(vol.Coerce(int), vol.Range(min=0, max=59)),
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_ABSENCE_PERIOD,
        handle_delete_absence_period,
        schema=vol.Schema(
            {CONFIG_ENTRY_FIELD: str, vol.Required(ATTR_INDEX): vol.All(vol.Coerce(int), vol.Range(min=0, max=6))}
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_DAY_STATISTICS,
        handle_get_day_statistics,
        schema=vol.Schema({CONFIG_ENTRY_FIELD: str, vol.Required(ATTR_DATE): str}),
        **_response_kwargs(),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_WEEK_STATISTICS,
        handle_get_week_statistics,
        schema=vol.Schema(
            {
                CONFIG_ENTRY_FIELD: str,
                vol.Required(ATTR_YEAR): vol.All(vol.Coerce(int), vol.Range(min=2000, max=2099)),
                vol.Required(ATTR_CALENDAR_WEEK): vol.All(vol.Coerce(int), vol.Range(min=1, max=53)),
            }
        ),
        **_response_kwargs(),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_MONTH_STATISTICS,
        handle_get_month_statistics,
        schema=vol.Schema(
            {
                CONFIG_ENTRY_FIELD: str,
                vol.Required(ATTR_YEAR): vol.All(vol.Coerce(int), vol.Range(min=2000, max=2099)),
                vol.Required(ATTR_MONTH): vol.All(vol.Coerce(int), vol.Range(min=1, max=12)),
            }
        ),
        **_response_kwargs(),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_YEAR_STATISTICS,
        handle_get_year_statistics,
        schema=vol.Schema(
            {
                CONFIG_ENTRY_FIELD: str,
                vol.Required(ATTR_YEAR): vol.All(vol.Coerce(int), vol.Range(min=2000, max=2099)),
            }
        ),
        **_response_kwargs(),
    )


def async_unload_services(hass: HomeAssistant) -> None:
    """Remove integration-level services."""
    for service in (
        SERVICE_SET_LEAKAGE_SETTINGS,
        SERVICE_SET_VACATION_MODE_TYPE,
        SERVICE_GET_DEVICE_DATETIME,
        SERVICE_SET_DEVICE_DATETIME,
        SERVICE_SYNC_DEVICE_DATETIME,
        SERVICE_GET_ABSENCE_PERIOD,
        SERVICE_SET_ABSENCE_PERIOD,
        SERVICE_DELETE_ABSENCE_PERIOD,
        SERVICE_GET_DAY_STATISTICS,
        SERVICE_GET_WEEK_STATISTICS,
        SERVICE_GET_MONTH_STATISTICS,
        SERVICE_GET_YEAR_STATISTICS,
    ):
        hass.services.async_remove(DOMAIN, service)


def _coordinator_from_call(hass: HomeAssistant, call: ServiceCall) -> JudoZewaDataUpdateCoordinator:
    """Resolve a service call to a coordinator."""
    entries: dict[str, JudoZewaDataUpdateCoordinator] = hass.data.get(DOMAIN, {})
    requested = call.data.get(CONF_CONFIG_ENTRY_ID)
    if requested:
        if requested not in entries:
            raise HomeAssistantError(f"No JUDO ZEWA i-SAFE config entry with id {requested}")
        return entries[requested]

    coordinators = [value for value in entries.values() if isinstance(value, JudoZewaDataUpdateCoordinator)]
    if len(coordinators) == 1:
        return coordinators[0]
    if not coordinators:
        raise HomeAssistantError("No JUDO ZEWA i-SAFE device is configured")
    raise HomeAssistantError("Multiple JUDO ZEWA i-SAFE devices are configured; pass config_entry_id")


def _parse_date(value: Any) -> date:
    """Parse Home Assistant service date input."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise HomeAssistantError("date must be an ISO date string, for example 2026-06-15")


def _parse_datetime(value: Any) -> datetime:
    """Parse Home Assistant service datetime input as device-local datetime."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value)
    else:
        raise HomeAssistantError("datetime must be an ISO datetime string")

    if parsed.tzinfo is not None:
        parsed = dt_util.as_local(parsed).replace(tzinfo=None)
    return parsed.replace(microsecond=0)

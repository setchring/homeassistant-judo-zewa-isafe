"""Data coordinator for the JUDO ZEWA i-SAFE integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CannotConnect, JudoZewaApi
from .cloud_api import JudoJuControlCloudApi
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class JudoZewaDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch and cache values from the JUDO device."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: JudoZewaApi,
        scan_interval: int,
        cloud_api: JudoJuControlCloudApi | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self.cloud_api = cloud_api
        self.identity = None

    async def _async_setup(self) -> None:
        """Load static identity before the first refresh."""
        self.identity = await self.api.async_validate()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the device."""
        try:
            absence_limits = await self.api.async_read_absence_limits()
            learning_active, learning_remaining_m3 = await self.api.async_read_learning()
            data = {
                "device_type": self.identity.device_type if self.identity else None,
                "device_type_name": self.identity.device_type_name if self.identity else None,
                "serial_number": self.identity.serial_number if self.identity else None,
                "sw_version": self.identity.sw_version if self.identity else None,
                "install_date": await self.api.async_read_install_date(),
                "total_water_m3": await self.api.async_read_total_water_m3(),
                "absence_flow_l_h": absence_limits.flow_l_h,
                "absence_volume_l": absence_limits.volume_l,
                "absence_duration_min": absence_limits.duration_min,
                "sleep_duration_hours": await self.api.async_read_sleep_duration_hours(),
                "learning_active": learning_active,
                "learning_remaining_m3": learning_remaining_m3,
                "microleakage_mode": await self.api.async_read_microleakage_mode(),
                "device_datetime": await self.api.async_read_device_datetime(),
                "absence_periods": await self.api.async_read_absence_periods(),
                "cloud_enabled": self.cloud_api is not None,
                "valve_open": None,
                "valve_cloud_error": None,
            }

            if self.cloud_api is not None:
                try:
                    valve_state = await self.cloud_api.async_read_valve_state()
                except Exception as err:  # noqa: BLE001 - keep local device data alive if cloud fails
                    _LOGGER.warning("Could not read JU-Control valve state: %s", err)
                    data["valve_cloud_error"] = str(err)[:200]
                else:
                    data.update(
                        {
                            "valve_open": valve_state.valve_open,
                            "valve_cloud_device_status": valve_state.device_status,
                            "valve_cloud_ewuid": valve_state.ewuid,
                            "valve_cloud_serial_number": valve_state.cloud_serial_number,
                            "valve_cloud_devnumber": valve_state.devnumber,
                            "valve_cloud_status_byte_23": valve_state.status_byte_23,
                            "valve_cloud_status_block_150": valve_state.status_block_150,
                            "valve_cloud_last_update": valve_state.last_cloud_update,
                            "valve_cloud_updated_at": valve_state.updated_at,
                            "microleakage_ok": valve_state.microleakage_ok,
                            "microleakage_status_byte_20": valve_state.status_byte_20,
                        }
                    )

            return data
        except CannotConnect as err:
            raise UpdateFailed(str(err)) from err

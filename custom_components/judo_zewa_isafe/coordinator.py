"""Data coordinator for the JUDO ZEWA i-SAFE integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CannotConnect, JudoZewaApi
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class JudoZewaDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch and cache values from the JUDO device."""

    def __init__(self, hass: HomeAssistant, api: JudoZewaApi, scan_interval: int) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self.identity = None

    async def _async_setup(self) -> None:
        """Load static identity before the first refresh."""
        self.identity = await self.api.async_validate()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the device."""
        try:
            absence_limits = await self.api.async_read_absence_limits()
            learning_active, learning_remaining_m3 = await self.api.async_read_learning()
            return {
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
            }
        except CannotConnect as err:
            raise UpdateFailed(str(err)) from err

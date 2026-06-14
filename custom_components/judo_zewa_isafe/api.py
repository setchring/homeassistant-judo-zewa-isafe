"""Local REST API client for JUDO ZEWA i-SAFE devices."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import aiohttp
import async_timeout

from .const import DEFAULT_TIMEOUT, SUPPORTED_DEVICE_TYPE_NAMES, SUPPORTED_DEVICE_TYPES

_LOGGER = logging.getLogger(__name__)


class JudoZewaApiError(Exception):
    """Base class for JUDO API errors."""


class CannotConnect(JudoZewaApiError):
    """Raised when the device cannot be reached."""


class InvalidAuth(JudoZewaApiError):
    """Raised when the credentials are rejected."""


class UnsupportedDevice(JudoZewaApiError):
    """Raised when the device type is not supported by this integration."""


@dataclass(slots=True)
class DeviceIdentity:
    """Static device identity returned by the device."""

    device_type: int
    device_type_name: str
    serial_number: str | None
    sw_version: str | None


@dataclass(slots=True)
class AbsenceLimits:
    """Absence/leakage limit settings."""

    flow_l_h: int | None
    volume_l: int | None
    duration_min: int | None


class JudoZewaApi:
    """Small async client for the local /api/rest endpoint."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int = 80,
        username: str | None = None,
        password: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._host = host.strip()
        self._port = int(port)
        self._timeout = int(timeout)
        self._auth = aiohttp.BasicAuth(username or "", password or "") if username or password else None
        self._base_url = f"http://{self._host}:{self._port}/api/rest"

    @property
    def host(self) -> str:
        """Return the configured host."""
        return self._host

    async def async_request(self, command: str) -> str | None:
        """Execute a raw REST command and return the JSON 'data' field."""
        url = f"{self._base_url}/{command.upper()}"
        _LOGGER.debug("Sending JUDO command %s", command.upper())

        try:
            async with async_timeout.timeout(self._timeout):
                response = await self._session.get(url, auth=self._auth)
                async with response:
                    if response.status in (401, 403):
                        raise InvalidAuth("Invalid JUDO credentials")
                    if response.status != 200:
                        raise CannotConnect(f"JUDO API returned HTTP {response.status}")
                    payload: dict[str, Any] = await response.json(content_type=None)
        except InvalidAuth:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise CannotConnect(str(err)) from err
        except ValueError as err:
            raise CannotConnect("JUDO API did not return JSON") from err

        if "errors" in payload and payload["errors"]:
            _LOGGER.debug("JUDO API returned errors for %s: %s", command, payload["errors"])

        data = payload.get("data")
        if data is None:
            return None
        return str(data).strip().replace(" ", "").upper()

    async def async_validate(self) -> DeviceIdentity:
        """Validate connectivity and return static identity."""
        device_type_raw = await self.async_request("FF00")
        if not device_type_raw:
            raise CannotConnect("Could not read JUDO device type")
        try:
            device_type = int(device_type_raw[0:2], 16)
        except ValueError as err:
            raise CannotConnect(f"Unexpected device type response: {device_type_raw}") from err

        if device_type not in SUPPORTED_DEVICE_TYPES:
            raise UnsupportedDevice(f"Unsupported JUDO device type 0x{device_type:02X}")

        serial = await self.async_read_serial_number()
        sw_version = await self.async_read_software_version()
        return DeviceIdentity(
            device_type=device_type,
            device_type_name=SUPPORTED_DEVICE_TYPE_NAMES.get(device_type, f"0x{device_type:02X}"),
            serial_number=serial,
            sw_version=sw_version,
        )

    async def async_read_serial_number(self) -> str | None:
        """Read the device serial number."""
        data = await self.async_request("0600")
        if not data:
            return None
        value = _little_uint(data, 0, 4)
        return str(value) if value is not None else None

    async def async_read_software_version(self) -> str | None:
        """Read the control-board software version."""
        data = await self.async_request("0100")
        return _parse_software_version(data)

    async def async_read_install_date(self) -> datetime | None:
        """Read the commissioning timestamp."""
        data = await self.async_request("0E00")
        if not data or len(data) < 8:
            return None
        try:
            timestamp = int(data[0:8], 16)
        except ValueError:
            return None
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    async def async_read_total_water_m3(self) -> float | None:
        """Read total water volume in m³."""
        data = await self.async_request("2800")
        liters = _little_uint(data, 0, 4)
        return round(liters / 1000, 3) if liters is not None else None

    async def async_read_absence_limits(self) -> AbsenceLimits:
        """Read absence limits: flow, volume, duration."""
        data = await self.async_request("5E00")
        return AbsenceLimits(
            flow_l_h=_little_uint(data, 0, 2),
            volume_l=_little_uint(data, 2, 2),
            duration_min=_little_uint(data, 4, 2),
        )

    async def async_set_absence_limits(self, flow_l_h: int, volume_l: int, duration_min: int) -> None:
        """Write absence limits."""
        payload = f"{_le_hex(flow_l_h, 2)}{_le_hex(volume_l, 2)}{_le_hex(duration_min, 2)}"
        await self.async_request(f"5F00{payload}")

    async def async_read_sleep_duration_hours(self) -> int | None:
        """Read sleep-mode duration in hours."""
        data = await self.async_request("6600")
        if not data:
            return None
        try:
            return int(data[0:2], 16)
        except ValueError:
            return None

    async def async_set_sleep_duration_hours(self, hours: int) -> None:
        """Write sleep-mode duration in hours."""
        await self.async_request(f"5300{_le_hex(hours, 1)}")

    async def async_read_learning(self) -> tuple[bool | None, float | None]:
        """Read learning-mode state and remaining learning water in m³."""
        data = await self.async_request("6400")
        if not data:
            return None, None
        try:
            active = int(data[0:2], 16) == 1
        except ValueError:
            active = None
        remaining_l = _little_uint(data, 1, 2)
        remaining_m3 = round(remaining_l / 1000, 3) if remaining_l is not None else None
        return active, remaining_m3

    async def async_read_microleakage_mode(self) -> int | None:
        """Read automatic micro-leakage-test mode."""
        data = await self.async_request("6500")
        if not data:
            return None
        try:
            return int(data[0:2], 16)
        except ValueError:
            return None

    async def async_set_microleakage_mode(self, mode: int) -> None:
        """Write automatic micro-leakage-test mode."""
        await self.async_request(f"5B00{_le_hex(mode, 1)}")

    async def async_press_button(self, command: str) -> None:
        """Execute a command button."""
        await self.async_request(command)



def _little_uint(data: str | None, byte_offset: int, byte_length: int) -> int | None:
    """Parse little-endian unsigned integer from a hex string."""
    if not data:
        return None
    start = byte_offset * 2
    end = start + byte_length * 2
    chunk = data[start:end]
    if len(chunk) != byte_length * 2:
        return None
    try:
        return int(bytes.fromhex(chunk)[::-1].hex(), 16)
    except ValueError:
        return None



def _le_hex(value: int | float, byte_length: int) -> str:
    """Format an integer as little-endian uppercase hex."""
    integer = int(round(float(value)))
    if integer < 0 or integer >= 1 << (8 * byte_length):
        raise ValueError(f"Value {integer} does not fit into {byte_length} byte(s)")
    return integer.to_bytes(byte_length, byteorder="little", signed=False).hex().upper()



def _parse_software_version(data: str | None) -> str | None:
    """Parse JUDO's 3-byte SW version format, e.g. 661301 -> 1.19f."""
    if not data or len(data) < 6:
        return None
    try:
        little = bytes.fromhex(data[0:6])[::-1]
        major = little[0]
        minor = little[1]
        suffix = chr(little[2]) if 32 <= little[2] <= 126 else f"{little[2]:02X}"
    except ValueError:
        return None
    return f"{major}.{minor:02d}{suffix}"

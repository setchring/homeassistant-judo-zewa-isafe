"""Local REST API client for JUDO ZEWA i-SAFE devices."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
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


@dataclass(slots=True)
class AbsencePeriod:
    """One programmable absence time period."""

    index: int
    enabled: bool
    start_day: int | None = None
    start_hour: int | None = None
    start_minute: int | None = None
    stop_day: int | None = None
    stop_hour: int | None = None
    stop_minute: int | None = None

    @property
    def state(self) -> str:
        """Return a compact human-readable state."""
        if not self.enabled:
            return "Aus"
        return (
            f"{WEEKDAY_NAMES[self.start_day]} {self.start_hour:02d}:{self.start_minute:02d}"
            f" bis {WEEKDAY_NAMES[self.stop_day]} {self.stop_hour:02d}:{self.stop_minute:02d}"
        )

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "index": self.index,
            "enabled": self.enabled,
            "start_day": self.start_day,
            "start_day_name": WEEKDAY_NAMES.get(self.start_day) if self.start_day is not None else None,
            "start_hour": self.start_hour,
            "start_minute": self.start_minute,
            "stop_day": self.stop_day,
            "stop_day_name": WEEKDAY_NAMES.get(self.stop_day) if self.stop_day is not None else None,
            "stop_hour": self.stop_hour,
            "stop_minute": self.stop_minute,
            "state": self.state,
        }


WEEKDAY_NAMES: dict[int | None, str] = {
    0: "So",
    1: "Mo",
    2: "Di",
    3: "Mi",
    4: "Do",
    5: "Fr",
    6: "Sa",
}

DAY_BUCKET_LABELS = ("00:00", "03:00", "06:00", "09:00", "12:00", "15:00", "18:00", "21:00")
WEEKDAY_BUCKET_LABELS = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
MONTH_BUCKET_LABELS = tuple(str(day) for day in range(1, 32))
YEAR_BUCKET_LABELS = ("Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez")


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

    async def async_set_leakage_settings(
        self,
        vacation_mode_type: int,
        flow_l_h: int,
        volume_l: int,
        duration_min: int,
    ) -> None:
        """Write all leakage settings using command 50."""
        _require_range("vacation_mode_type", vacation_mode_type, 0, 3)
        payload = (
            f"{_le_hex(vacation_mode_type, 1)}"
            f"{_le_hex(flow_l_h, 2)}"
            f"{_le_hex(volume_l, 2)}"
            f"{_le_hex(duration_min, 2)}"
        )
        await self.async_request(f"5000{payload}")

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
        _require_range("hours", hours, 1, 10)
        await self.async_request(f"5300{_le_hex(hours, 1)}")

    async def async_set_vacation_mode_type(self, mode: int) -> None:
        """Write vacation-mode type: 0=off, 1=U1, 2=U2, 3=U3."""
        _require_range("mode", mode, 0, 3)
        await self.async_request(f"5600{_le_hex(mode, 1)}")

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
        _require_range("mode", mode, 0, 2)
        await self.async_request(f"5B00{_le_hex(mode, 1)}")

    async def async_read_device_datetime(self) -> datetime | None:
        """Read device-local date/time from command 59."""
        data = await self.async_request("5900")
        if not data or len(data) < 12:
            return None
        try:
            day = int(data[0:2], 16)
            month = int(data[2:4], 16)
            year = 2000 + int(data[4:6], 16)
            hour = int(data[6:8], 16)
            minute = int(data[8:10], 16)
            second = int(data[10:12], 16)
            return datetime(year, month, day, hour, minute, second)
        except (ValueError, TypeError):
            return None

    async def async_set_device_datetime(self, value: datetime) -> None:
        """Write device-local date/time with command 5A."""
        payload = (
            f"{_le_hex(value.day, 1)}"
            f"{_le_hex(value.month, 1)}"
            f"{_le_hex(value.year % 100, 1)}"
            f"{_le_hex(value.hour, 1)}"
            f"{_le_hex(value.minute, 1)}"
            f"{_le_hex(value.second, 1)}"
        )
        await self.async_request(f"5A00{payload}")

    async def async_read_absence_period(self, index: int) -> AbsencePeriod:
        """Read one programmable absence period."""
        _require_range("index", index, 0, 6)
        data = await self.async_request(f"6000{_le_hex(index, 1)}")
        return _parse_absence_period(index, data)

    async def async_read_absence_periods(self) -> dict[int, AbsencePeriod]:
        """Read all seven programmable absence periods."""
        periods: dict[int, AbsencePeriod] = {}
        for index in range(7):
            periods[index] = await self.async_read_absence_period(index)
        return periods

    async def async_set_absence_period(
        self,
        index: int,
        start_day: int,
        start_hour: int,
        start_minute: int,
        stop_day: int,
        stop_hour: int,
        stop_minute: int,
    ) -> None:
        """Write one programmable absence period."""
        _require_range("index", index, 0, 6)
        _require_range("start_day", start_day, 0, 6)
        _require_range("start_hour", start_hour, 0, 23)
        _require_range("start_minute", start_minute, 0, 59)
        _require_range("stop_day", stop_day, 0, 6)
        _require_range("stop_hour", stop_hour, 0, 23)
        _require_range("stop_minute", stop_minute, 0, 59)
        payload = "".join(
            _le_hex(value, 1)
            for value in (index, start_day, start_hour, start_minute, stop_day, stop_hour, stop_minute)
        )
        await self.async_request(f"6100{payload}")

    async def async_delete_absence_period(self, index: int) -> None:
        """Delete one programmable absence period."""
        _require_range("index", index, 0, 6)
        await self.async_request(f"6200{_le_hex(index, 1)}")

    async def async_read_day_statistics(self, statistic_date: date) -> dict[str, Any]:
        """Read day water-consumption statistics in liters."""
        data = await self.async_request(
            f"FB00{_le_hex(statistic_date.day, 1)}{_le_hex(statistic_date.month, 1)}{_be_hex(statistic_date.year, 2)}"
        )
        values = _parse_fixed_liter_values(data, DAY_BUCKET_LABELS)
        return {
            "date": statistic_date.isoformat(),
            "unit": "L",
            "buckets": values,
            "total_l": sum(values.values()),
        }

    async def async_read_week_statistics(self, year: int, calendar_week: int) -> dict[str, Any]:
        """Read week water-consumption statistics in liters."""
        _require_range("calendar_week", calendar_week, 1, 53)
        data = await self.async_request(f"FC00{_le_hex(calendar_week, 1)}{_be_hex(year, 2)}")
        values = _parse_fixed_liter_values(data, WEEKDAY_BUCKET_LABELS)
        return {
            "year": year,
            "calendar_week": calendar_week,
            "unit": "L",
            "days": values,
            "total_l": sum(values.values()),
        }

    async def async_read_month_statistics(self, year: int, month: int) -> dict[str, Any]:
        """Read month water-consumption statistics in liters."""
        _require_range("month", month, 1, 12)
        data = await self.async_request(f"FD00{_le_hex(month, 1)}{_be_hex(year, 2)}")
        values = _parse_fixed_liter_values(data, MONTH_BUCKET_LABELS)
        return {
            "year": year,
            "month": month,
            "unit": "L",
            "days": values,
            "total_l": sum(values.values()),
        }

    async def async_read_year_statistics(self, year: int) -> dict[str, Any]:
        """Read year water-consumption statistics in liters."""
        data = await self.async_request(f"FE00{_be_hex(year, 2)}")
        values = _parse_fixed_liter_values(data, YEAR_BUCKET_LABELS)
        return {
            "year": year,
            "unit": "L",
            "months": values,
            "total_l": sum(values.values()),
        }

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


def _be_hex(value: int | float, byte_length: int) -> str:
    """Format an integer as big-endian uppercase hex."""
    integer = int(round(float(value)))
    if integer < 0 or integer >= 1 << (8 * byte_length):
        raise ValueError(f"Value {integer} does not fit into {byte_length} byte(s)")
    return integer.to_bytes(byte_length, byteorder="big", signed=False).hex().upper()


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


def _parse_absence_period(index: int, data: str | None) -> AbsencePeriod:
    """Parse a six-byte absence-period response."""
    if not data or len(data) < 12:
        return AbsencePeriod(index=index, enabled=False)
    try:
        values = [int(data[position : position + 2], 16) for position in range(0, 12, 2)]
    except ValueError:
        return AbsencePeriod(index=index, enabled=False)

    if values == [0, 0, 0, 0, 0, 0]:
        return AbsencePeriod(index=index, enabled=False)

    start_day, start_hour, start_minute, stop_day, stop_hour, stop_minute = values
    if not (0 <= start_day <= 6 and 0 <= stop_day <= 6 and 0 <= start_hour <= 23 and 0 <= stop_hour <= 23):
        return AbsencePeriod(index=index, enabled=False)
    if not (0 <= start_minute <= 59 and 0 <= stop_minute <= 59):
        return AbsencePeriod(index=index, enabled=False)

    return AbsencePeriod(
        index=index,
        enabled=True,
        start_day=start_day,
        start_hour=start_hour,
        start_minute=start_minute,
        stop_day=stop_day,
        stop_hour=stop_hour,
        stop_minute=stop_minute,
    )


def _parse_fixed_liter_values(data: str | None, labels: tuple[str, ...]) -> dict[str, int]:
    """Parse fixed 4-byte little-endian liter buckets."""
    result: dict[str, int] = {}
    for index, label in enumerate(labels):
        result[label] = _little_uint(data, index * 4, 4) or 0
    return result


def _require_range(name: str, value: int, minimum: int, maximum: int) -> None:
    """Raise ValueError if a numeric API argument is outside the allowed range."""
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")

"""Read-only JUDO JU-Control cloud client for valve-state polling."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import aiohttp

from .api import CannotConnect, InvalidAuth
from .const import (
    DEFAULT_CLOUD_APPLICATION,
    DEFAULT_CLOUD_BASE_URL,
    DEFAULT_CLOUD_LANGUAGE,
    DEFAULT_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class JudoCloudValveState:
    """Valve state derived from JU-Control cloud data."""

    valve_open: bool | None
    device_status: str | None
    ewuid: str | None
    cloud_serial_number: str | None
    devnumber: str | None
    status_block_150: str | None
    status_byte_23: int | None
    last_cloud_update: str | None
    updated_at: datetime
    microleakage_ok: bool | None
    status_byte_20: int | None


class JudoJuControlCloudApi:
    """Read-only client for https://www.myjudo.eu/interface/."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        *,
        base_url: str = DEFAULT_CLOUD_BASE_URL,
        language: str = DEFAULT_CLOUD_LANGUAGE,
        application: str = DEFAULT_CLOUD_APPLICATION,
        timeout: int = DEFAULT_TIMEOUT,
        device_hint: str | None = None,
    ) -> None:
        """Initialize the cloud client."""
        self._session = session
        self._username = username.strip()
        self._password = password
        self._base_url = base_url
        self._language = language
        self._application = application
        self._timeout = timeout
        self._device_hint = (device_hint or "").strip() or None
        self._token: str | None = None

    async def async_validate(self) -> None:
        """Validate credentials and ensure device data is readable."""
        await self.async_login(force=True)
        await self.async_read_valve_state()

    async def async_login(self, *, force: bool = False) -> str:
        """Log in and return a JU-Control token."""
        if self._token and not force:
            return self._token

        password_hash = hashlib.md5(self._password.strip().encode("utf-8")).hexdigest()
        payload = await self._async_request(
            {
                "group": "register",
                "command": "login",
                "name": "login",
                "user": self._username,
                "password": password_hash,
                "role": "customer",
                "application": self._application,
                "language": self._language,
            },
            include_token=False,
        )

        token = _find_token(payload)
        if not token:
            raise InvalidAuth("JU-Control login did not return a token")

        if str(payload.get("status", "")).lower() not in ("ok", "success", ""):
            raise InvalidAuth("JU-Control login was rejected")

        self._token = token
        return token

    async def async_read_valve_state(self) -> JudoCloudValveState:
        """Read the cloud device data and derive the valve state."""
        token = await self.async_login()

        try:
            payload = await self._async_request(
                {
                    "token": token,
                    "group": "register",
                    "command": "get device data",
                },
                include_token=True,
            )
        except InvalidAuth:
            self._token = None
            token = await self.async_login(force=True)
            payload = await self._async_request(
                {
                    "token": token,
                    "group": "register",
                    "command": "get device data",
                },
                include_token=True,
            )

        device = _select_device(payload, self._device_hint)
        register = _first_register(device)

        nested_data = register.get("data") if isinstance(register, dict) else {}
        if not isinstance(nested_data, dict):
            nested_data = {}

        block_150 = _extract_hex_data(nested_data.get("150"))
        status_byte = _status_byte(block_150, 23)

        # Get notification OK flag
        snippet = block_150[44:52]

        # Convert hex string to integer
        val = int(snippet, 16)

        # Convert integer to 4 bytes in Big-Endian, then swap to Little-Endian
        # 'big' -> 'little' effectively reverses the byte order
        swapped_bytes = val.to_bytes(4, byteorder='big')[::-1]

        # Convert back to hex string
        swapped = swapped_bytes.hex().upper()

        print(swapped)

        # Convert hex string to decimal integer
        decimal_val = int(swapped, 16)
        print(decimal_val)

        binary_val = bin(decimal_val)

        print(binary_val)
        # Output: 0b1000000000100000000000000

        # Optional: Remove '0b' prefix and pad to 32 bits (4 bytes)
        binary_padded = binary_val[2:].zfill(32)

        status_byte_20 = int(binary_padded[21])

        microleakage_ok = None

        if status_byte_20 is not None:
            microleakage_ok = bool(status_byte_20)
        valve_open = _valve_open_from_status_byte(status_byte)

        return JudoCloudValveState(
            valve_open=valve_open,
            device_status=_as_str(device.get("status")),
            ewuid=_as_str(device.get("ewuid")),
            cloud_serial_number=_as_str(device.get("serialnumber")),
            devnumber=_as_str(device.get("devnumber")),
            status_block_150=block_150,
            status_byte_23=status_byte,
            last_cloud_update=_as_str(nested_data.get("lu")),
            updated_at=datetime.now(timezone.utc),
            microleakage_ok=microleakage_ok,
            status_byte_20=status_byte_20,
        )

    async def _async_request(self, params: dict[str, Any], *, include_token: bool) -> dict[str, Any]:
        """Call the JU-Control interface without logging secrets."""
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
        }

        try:
            async with asyncio.timeout(self._timeout):
                response = await self._session.get(self._base_url, params=params, headers=headers)
                async with response:
                    if response.status in (401, 403):
                        raise InvalidAuth("JU-Control credentials were rejected")
                    if response.status != 200:
                        raise CannotConnect(f"JU-Control API returned HTTP {response.status}")
                    payload = await response.json(content_type=None)
        except InvalidAuth:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise CannotConnect(str(err)) from err
        except ValueError as err:
            raise CannotConnect("JU-Control API did not return JSON") from err

        if not isinstance(payload, dict):
            raise CannotConnect("JU-Control API returned an unexpected response")

        status = str(payload.get("status", "")).lower()
        if status in {"error", "failed", "fail"}:
            message = payload.get("message") or payload.get("error") or "JU-Control API returned an error"
            raise InvalidAuth(str(message)[:200])

        if include_token and "token" in payload and payload.get("token"):
            self._token = str(payload["token"])

        return payload


def _find_token(payload: dict[str, Any]) -> str | None:
    """Find a token in known JU-Control response layouts."""
    token = payload.get("token")
    if token:
        return str(token)

    data = payload.get("data")
    if isinstance(data, dict):
        token = data.get("token")
        if token:
            return str(token)
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("token"):
                return str(item["token"])
    return None


def _select_device(payload: dict[str, Any], hint: str | None) -> dict[str, Any]:
    """Select the ZEWA/PROM device from a cloud response."""
    data = payload.get("data")
    if not isinstance(data, list):
        raise CannotConnect("JU-Control response does not contain device data")

    candidates: list[dict[str, Any]] = [item for item in data if isinstance(item, dict)]

    if hint:
        hint_lower = hint.lower()
        for item in candidates:
            values = (
                item.get("serialnumber"),
                item.get("serial number"),
                item.get("devnumber"),
                item.get("ewuid"),
            )
            if any(str(value).lower() == hint_lower for value in values if value is not None):
                return item

    zewa_candidates: list[dict[str, Any]] = []
    for item in candidates:
        for register in item.get("data", []) if isinstance(item.get("data"), list) else []:
            if isinstance(register, dict) and str(register.get("dt", "")).lower() == "0x44":
                zewa_candidates.append(item)
                break

    if zewa_candidates:
        return zewa_candidates[0]
    if candidates:
        return candidates[0]

    raise CannotConnect("JU-Control account does not contain a readable device")


def _first_register(device: dict[str, Any]) -> dict[str, Any]:
    """Return the first nested register block."""
    registers = device.get("data")
    if isinstance(registers, list):
        for register in registers:
            if isinstance(register, dict):
                return register
    raise CannotConnect("JU-Control device response has no register data")


def _extract_hex_data(value: Any) -> str | None:
    """Extract and normalize a nested hex data field."""
    if isinstance(value, dict):
        value = value.get("data")
    if value is None:
        return None
    text = str(value).strip().replace(" ", "").upper()
    return text or None


def _status_byte(block: str | None, index: int) -> int | None:
    """Return one byte from a hex block."""
    if not block or len(block) < (index + 1) * 2:
        return None
    try:
        return int(block[index * 2 : index * 2 + 2], 16)
    except ValueError:
        return None


def _valve_open_from_status_byte(status_byte: int | None) -> bool | None:
    """Derive valve state from the observed JU-Control ZEWA 2021 status byte.

    Observed with ZEWA i-SAFE FILT / dt=0x44:
    - closed: byte 23 has bit 0x80 set
    - open/normal: bit 0x80 is not set
    """
    if status_byte is None:
        return None
    return (status_byte & 0x80) == 0


def _as_str(value: Any) -> str | None:
    """Return a value as string if present."""
    if value is None:
        return None
    return str(value)

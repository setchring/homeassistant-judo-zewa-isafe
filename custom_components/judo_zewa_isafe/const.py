"""Constants for the JUDO ZEWA i-SAFE integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SCAN_INTERVAL, CONF_USERNAME

DOMAIN = "judo_zewa_isafe"
NAME = "JUDO ZEWA i-SAFE"
DEFAULT_PORT = 80
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "Connectivity"
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 30
DEFAULT_TIMEOUT = 10

SUPPORTED_DEVICE_TYPES = {0x44, 0x68}
SUPPORTED_DEVICE_TYPE_NAMES = {
    0x44: "ZEWA i-SAFE / ZEWA i-SAFE FILT / PROM-i-SAFE",
    0x68: "ZEWA / PROM-i-SAFE",
}

CONF_KEYS = {CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_PASSWORD, CONF_SCAN_INTERVAL}

PLATFORMS = ["sensor", "binary_sensor", "button", "number", "select"]

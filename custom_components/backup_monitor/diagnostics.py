from __future__ import annotations

from copy import deepcopy
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN

REDACT_KEYS = {
    CONF_PASSWORD,
    CONF_USERNAME,
    "access_token",
    "accessToken",
    "token",
    "Authorization",
    "authorization",
    "cookie",
    "Cookie",
    "set-cookie",
    "Set-Cookie",
    "refresh_token",
    "RefreshToken",
    "RefreshNonce",
    "refresh_nonce",
}


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if key in REDACT_KEYS:
                redacted[key] = "REDACTED"
            else:
                redacted[key] = _redact(item)
        return redacted

    if isinstance(value, list):
        return [_redact(item) for item in value]

    return value


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    entry_data = deepcopy(dict(entry.data))
    options_data = deepcopy(dict(entry.options))

    if CONF_PASSWORD in entry_data:
        entry_data[CONF_PASSWORD] = "REDACTED"
    if CONF_USERNAME in entry_data:
        entry_data[CONF_USERNAME] = "REDACTED"

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    coordinator_data = _redact(deepcopy(coordinator.data))

    return {
        "entry": entry_data,
        "options": options_data,
        "coordinator_data": coordinator_data,
        "integration_domain": DOMAIN,
        "entry_id": entry.entry_id,
        "title": entry.title,
    }
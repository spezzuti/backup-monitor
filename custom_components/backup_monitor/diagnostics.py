from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    data = dict(entry.data)
    if CONF_PASSWORD in data:
        data[CONF_PASSWORD] = "REDACTED"
    if CONF_USERNAME in data:
        data[CONF_USERNAME] = "REDACTED"
    return {"entry": data, "options": dict(entry.options), "data": coordinator.data}

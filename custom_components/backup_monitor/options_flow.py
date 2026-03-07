from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries

from .const import (
    CONF_POLL_INTERVAL,
    CONF_STALE_HOURS,
    CONF_VERIFY_SSL,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_STALE_HOURS,
)


class BackupMonitorOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(CONF_POLL_INTERVAL, default=self._entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)): vol.All(int, vol.Range(min=10, max=3600)),
                vol.Optional(CONF_STALE_HOURS, default=self._entry.options.get(CONF_STALE_HOURS, DEFAULT_STALE_HOURS)): vol.All(int, vol.Range(min=1, max=720)),
                vol.Optional(CONF_VERIFY_SSL, default=self._entry.options.get(CONF_VERIFY_SSL, self._entry.data.get(CONF_VERIFY_SSL, True))): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

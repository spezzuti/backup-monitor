from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries

from .const import (
    CONF_BASE_URL,
    CONF_PASSWORD,
    CONF_PROVIDER,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    PROVIDER_BACKREST,
    PROVIDER_DUPLICATI,
)
from .providers.backrest import BackrestClient
from .providers.duplicati import DuplicatiClient
from .options_flow import BackupMonitorOptionsFlow

_LOGGER = logging.getLogger(__name__)

PROVIDER_SCHEMA = vol.Schema({vol.Required(CONF_PROVIDER): vol.In([PROVIDER_BACKREST, PROVIDER_DUPLICATI])})

BACKREST_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BASE_URL): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    }
)

DUPLICATI_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BASE_URL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    }
)


class BackupMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._provider: str | None = None

    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=PROVIDER_SCHEMA)

        self._provider = user_input[CONF_PROVIDER]
        if self._provider == PROVIDER_BACKREST:
            return await self.async_step_backrest()
        return await self.async_step_duplicati()

    async def async_step_backrest(self, user_input=None):
        errors = {}
        if user_input is not None:
            client = BackrestClient(self.hass, _fake_entry(self._provider, user_input))
            try:
                await client.async_validate()
            except Exception as e:  # noqa: BLE001
                _LOGGER.exception("Backrest validation failed: %s", e)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=user_input.get(CONF_BASE_URL, "Backrest"),
                    data={CONF_PROVIDER: PROVIDER_BACKREST, **user_input},
                )
        return self.async_show_form(step_id="backrest", data_schema=BACKREST_SCHEMA, errors=errors)

    async def async_step_duplicati(self, user_input=None):
        errors = {}
        if user_input is not None:
            client = DuplicatiClient(self.hass, _fake_entry(self._provider, user_input))
            try:
                await client.async_validate()
            except Exception as e:  # noqa: BLE001
                _LOGGER.exception("Duplicati validation failed: %s", e)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=user_input.get(CONF_BASE_URL, "Duplicati"),
                    data={CONF_PROVIDER: PROVIDER_DUPLICATI, **user_input},
                )
        return self.async_show_form(step_id="duplicati", data_schema=DUPLICATI_SCHEMA, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry):
        return BackupMonitorOptionsFlow(config_entry)


def _fake_entry(provider: str, data: dict):
    class _E:
        def __init__(self, data):
            self.data = {CONF_PROVIDER: provider, **data}
            self.options = {}
            self.entry_id = "validation"
            self.title = data.get(CONF_BASE_URL, provider)
    return _E(data)

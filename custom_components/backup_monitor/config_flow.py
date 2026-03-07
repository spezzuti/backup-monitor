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
from .options_flow import BackupMonitorOptionsFlow
from .providers.backrest import BackrestClient
from .providers.duplicati import DuplicatiClient

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
        self._reauth_entry = None

    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=PROVIDER_SCHEMA)

        self._provider = user_input[CONF_PROVIDER]
        if self._provider == PROVIDER_BACKREST:
            return await self.async_step_backrest()
        return await self.async_step_duplicati()

    async def async_step_reauth(self, entry_data):
        """Handle reauthentication flow start."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        if self._reauth_entry is None:
            return self.async_abort(reason="unknown")

        self._provider = self._reauth_entry.data[CONF_PROVIDER]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Handle reauthentication confirmation."""
        if self._reauth_entry is None:
            return self.async_abort(reason="unknown")

        errors = {}

        provider = self._reauth_entry.data[CONF_PROVIDER]

        if provider == PROVIDER_BACKREST:
            schema = vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=self._reauth_entry.data.get(CONF_USERNAME, ""),
                    ): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(
                        CONF_VERIFY_SSL,
                        default=self._reauth_entry.options.get(
                            CONF_VERIFY_SSL,
                            self._reauth_entry.data.get(CONF_VERIFY_SSL, True),
                        ),
                    ): bool,
                }
            )

            if user_input is not None:
                new_data = {
                    **self._reauth_entry.data,
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
                }
                client = BackrestClient(self.hass, _fake_entry(provider, new_data))
                try:
                    await client.async_validate()
                except Exception as e:  # noqa: BLE001
                    _LOGGER.exception("Backrest reauth failed: %s", e)
                    errors["base"] = "cannot_connect"
                else:
                    self.hass.config_entries.async_update_entry(
                        self._reauth_entry,
                        data=new_data,
                    )
                    await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                    return self.async_abort(reason="reauth_successful")

            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=schema,
                errors=errors,
            )

        if provider == PROVIDER_DUPLICATI:
            schema = vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(
                        CONF_VERIFY_SSL,
                        default=self._reauth_entry.options.get(
                            CONF_VERIFY_SSL,
                            self._reauth_entry.data.get(CONF_VERIFY_SSL, True),
                        ),
                    ): bool,
                }
            )

            if user_input is not None:
                new_data = {
                    **self._reauth_entry.data,
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
                }
                client = DuplicatiClient(self.hass, _fake_entry(provider, new_data))
                try:
                    await client.async_validate()
                except Exception as e:  # noqa: BLE001
                    _LOGGER.exception("Duplicati reauth failed: %s", e)
                    errors["base"] = "cannot_connect"
                else:
                    self.hass.config_entries.async_update_entry(
                        self._reauth_entry,
                        data=new_data,
                    )
                    await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                    return self.async_abort(reason="reauth_successful")

            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=schema,
                errors=errors,
            )

        return self.async_abort(reason="unknown")

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

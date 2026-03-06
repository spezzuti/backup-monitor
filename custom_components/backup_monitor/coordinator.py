from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_PROVIDER,
    CONF_POLL_INTERVAL,
    DOMAIN,
    PROVIDER_BACKREST,
    PROVIDER_DUPLICATI,
)
from .providers.backrest import BackrestClient
from .providers.duplicati import DuplicatiClient

_LOGGER = logging.getLogger(__name__)


class BackupMonitorCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client) -> None:
        self.entry = entry
        self.client = client
        poll = entry.options.get(CONF_POLL_INTERVAL, entry.data.get(CONF_POLL_INTERVAL, 60))
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}-{entry.title}",
            update_interval=timedelta(seconds=int(poll)),
        )

    async def _async_update_data(self) -> dict:
        return await self.client.async_fetch()


async def create_coordinator(hass: HomeAssistant, entry: ConfigEntry) -> BackupMonitorCoordinator:
    provider = entry.data[CONF_PROVIDER]
    if provider == PROVIDER_BACKREST:
        client = BackrestClient(hass, entry)
    elif provider == PROVIDER_DUPLICATI:
        client = DuplicatiClient(hass, entry)
    else:
        raise ValueError(f"Unknown provider: {provider}")
    return BackupMonitorCoordinator(hass, entry, client)

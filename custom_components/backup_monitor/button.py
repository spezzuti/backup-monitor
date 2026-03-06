from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, PROVIDER_BACKREST, PROVIDER_DUPLICATI
from .entity import BackupMonitorEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    await coordinator.async_refresh()
    provider = entry.data["provider"]

    created: set[str] = set()

    def add_for_ids(ids: list[str], name_map: dict[str, str] | None = None) -> None:
        new_ents: list[ButtonEntity] = []
        for _id in ids:
            if _id in created:
                continue
            created.add(_id)
            nm = name_map.get(_id) if name_map else _id
            new_ents.append(RunNowButton(coordinator, provider, _id, nm))
        if new_ents:
            async_add_entities(new_ents)

    def snapshot() -> None:
        data = coordinator.data or {}
        if provider == PROVIDER_BACKREST:
            add_for_ids(list((data.get("plans") or {}).keys()))
        elif provider == PROVIDER_DUPLICATI:
            jobs = data.get("jobs") or {}
            name_map = {jid: (st.get("name") or f"Job {jid}") for jid, st in jobs.items()}
            add_for_ids(list(jobs.keys()), name_map=name_map)

    snapshot()

    @callback
    def _handle_update() -> None:
        snapshot()

    entry.async_on_unload(coordinator.async_add_listener(_handle_update))


class RunNowButton(BackupMonitorEntity, ButtonEntity):
    _attr_icon = "mdi:play-circle-outline"

    def __init__(self, coordinator, provider: str, job_id: str, name: str) -> None:
        super().__init__(coordinator, provider, job_id, f"{name} run now")

    async def async_press(self) -> None:
        client = self.coordinator.client
        if self._provider == PROVIDER_BACKREST:
            await client.async_run_plan(self._job_id)
        elif self._provider == PROVIDER_DUPLICATI:
            await client.async_run_job(self._job_id)
        await self.coordinator.async_request_refresh()

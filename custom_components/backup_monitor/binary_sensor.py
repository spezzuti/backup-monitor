from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import CONF_STALE_HOURS, DEFAULT_STALE_HOURS, DOMAIN, PROVIDER_BACKREST, PROVIDER_DUPLICATI
from .entity import BackupMonitorEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    await coordinator.async_refresh()
    provider = entry.data["provider"]
    stale_hours = int(entry.options.get(CONF_STALE_HOURS, DEFAULT_STALE_HOURS))

    created: set[str] = set()

    def add_for_ids(ids: list[str], name_map: dict[str, str] | None = None) -> None:
        new_ents: list[BinarySensorEntity] = []
        for _id in ids:
            if _id in created:
                continue
            created.add(_id)
            nm = name_map.get(_id) if name_map else _id
            new_ents.append(BackupStaleBinarySensor(coordinator, provider, _id, nm, stale_hours))
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


class BackupStaleBinarySensor(BackupMonitorEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:alert"

    def __init__(self, coordinator, provider: str, job_id: str, name: str, stale_hours: int) -> None:
        super().__init__(coordinator, provider, job_id, f"{name} stale")
        self._stale_hours = stale_hours

    @property
    def is_on(self):
        st = _get_state(self.coordinator.data, self._provider, self._job_id)
        v = st.get("last_end")
        if not v:
            return True
        try:
            last = datetime.fromisoformat(v)
        except Exception:
            return True
        now = dt_util.utcnow()
        return (now - last) > timedelta(hours=self._stale_hours)


def _get_state(data: dict[str, Any] | None, provider: str, job_id: str) -> dict[str, Any]:
    data = data or {}
    if provider == PROVIDER_BACKREST:
        return (data.get("plans") or {}).get(job_id, {})
    return (data.get("jobs") or {}).get(job_id, {})

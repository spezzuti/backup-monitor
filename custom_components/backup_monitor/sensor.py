from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
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

    entities: list[SensorEntity] = [BackupCountSensor(coordinator, provider)]
    created.add("_count")

    def add_for_ids(ids: list[str], name_map: dict[str, str] | None = None) -> None:
        new_ents: list[SensorEntity] = []
        for _id in ids:
            if _id in created:
                continue
            created.add(_id)
            nm = name_map.get(_id) if name_map else _id
            new_ents.append(BackupLastResultSensor(coordinator, provider, _id, nm))
            new_ents.append(BackupLastSuccessSensor(coordinator, provider, _id, nm))
            new_ents.append(BackupLastDurationSensor(coordinator, provider, _id, nm))
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
    async_add_entities(entities)

    @callback
    def _handle_coordinator_update() -> None:
        snapshot()

    entry.async_on_unload(coordinator.async_add_listener(_handle_coordinator_update))


class BackupCountSensor(BackupMonitorEntity, SensorEntity):
    _attr_icon = "mdi:counter"

    def __init__(self, coordinator, provider: str) -> None:
        super().__init__(coordinator, provider, "_count", "Backup jobs count")

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        if self._provider == PROVIDER_BACKREST:
            return len((data.get("plans") or {}).keys())
        return len((data.get("jobs") or {}).keys())


class BackupLastResultSensor(BackupMonitorEntity, SensorEntity):
    _attr_icon = "mdi:backup-restore"

    def __init__(self, coordinator, provider: str, job_id: str, name: str) -> None:
        super().__init__(coordinator, provider, job_id, f"{name} last result")

    @property
    def native_value(self):
        st = _get_state(self.coordinator.data, self._provider, self._job_id)
        return st.get("last_status") or st.get("last_result")


class BackupLastSuccessSensor(BackupMonitorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, provider: str, job_id: str, name: str) -> None:
        super().__init__(coordinator, provider, job_id, f"{name} last success")

    @property
    def native_value(self):
        st = _get_state(self.coordinator.data, self._provider, self._job_id)
        v = st.get("last_end")
        if not v:
            return None
        try:
            return datetime.fromisoformat(v)
        except Exception:
            return None


class BackupLastDurationSensor(BackupMonitorEntity, SensorEntity):
    _attr_icon = "mdi:timer-outline"
    _attr_native_unit_of_measurement = "s"

    def __init__(self, coordinator, provider: str, job_id: str, name: str) -> None:
        super().__init__(coordinator, provider, job_id, f"{name} last duration")

    @property
    def native_value(self):
        st = _get_state(self.coordinator.data, self._provider, self._job_id)
        return st.get("duration_s")


def _get_state(data: dict[str, Any] | None, provider: str, job_id: str) -> dict[str, Any]:
    data = data or {}
    if provider == PROVIDER_BACKREST:
        return (data.get("plans") or {}).get(job_id, {})
    return (data.get("jobs") or {}).get(job_id, {})

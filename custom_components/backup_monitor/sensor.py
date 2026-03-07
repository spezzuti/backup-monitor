from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
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

    entities: list[SensorEntity] = [
        BackupCountSensor(coordinator, provider),
        ProviderFailedJobsSensor(coordinator, provider),
        ProviderSuccessfulJobsSensor(coordinator, provider),
        ProviderLastSuccessSensor(coordinator, provider),
        ProviderLastResultSensor(coordinator, provider),
    ]
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


class ProviderJobCountSensor(BackupMonitorEntity, SensorEntity):
    _attr_icon = "mdi:counter"

    def __init__(self, coordinator, provider: str) -> None:
        super().__init__(coordinator, provider, "_provider_job_count", "Job count")

    @property
    def native_value(self):
        jobs = _jobs_for_provider(self.coordinator.data, self._provider)
        return len(jobs)


class ProviderFailedJobsSensor(BackupMonitorEntity, SensorEntity):
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator, provider: str) -> None:
        super().__init__(coordinator, provider, "_provider_failed_jobs", "Failed jobs")

    @property
    def native_value(self):
        jobs = _jobs_for_provider(self.coordinator.data, self._provider)
        return len(_failed_jobs(jobs))


class ProviderSuccessfulJobsSensor(BackupMonitorEntity, SensorEntity):
    _attr_icon = "mdi:check-circle-outline"

    def __init__(self, coordinator, provider: str) -> None:
        super().__init__(coordinator, provider, "_provider_successful_jobs", "Successful jobs")

    @property
    def native_value(self):
        jobs = _jobs_for_provider(self.coordinator.data, self._provider)
        return len(_successful_jobs(jobs))


class ProviderLastSuccessSensor(BackupMonitorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, provider: str) -> None:
        super().__init__(coordinator, provider, "_provider_last_success", "Last success")

    @property
    def native_value(self):
        jobs = _jobs_for_provider(self.coordinator.data, self._provider)
        value = _latest_success_iso(jobs)
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None


class ProviderLastResultSensor(BackupMonitorEntity, SensorEntity):
    _attr_icon = "mdi:clipboard-check-outline"

    def __init__(self, coordinator, provider: str) -> None:
        super().__init__(coordinator, provider, "_provider_last_result", "Last result")

    @property
    def native_value(self):
        jobs = _jobs_for_provider(self.coordinator.data, self._provider)
        return _provider_result(jobs)


def _get_state(data: dict[str, Any] | None, provider: str, job_id: str) -> dict[str, Any]:
    data = data or {}
    if provider == PROVIDER_BACKREST:
        return (data.get("plans") or {}).get(job_id, {})
    return (data.get("jobs") or {}).get(job_id, {})


def _jobs_for_provider(data: dict[str, Any] | None, provider: str) -> dict[str, Any]:
    data = data or {}
    if provider == PROVIDER_BACKREST:
        return data.get("plans") or {}
    return data.get("jobs") or {}


def _successful_jobs(jobs: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        job for job in jobs.values()
        if isinstance(job, dict) and job.get("last_result") == "success"
    ]


def _failed_jobs(jobs: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        job for job in jobs.values()
        if isinstance(job, dict) and job.get("last_result") == "error"
    ]


def _latest_success_iso(jobs: dict[str, Any]) -> str | None:
    latest: str | None = None
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        value = job.get("last_end")
        if not value:
            continue
        if latest is None or str(value) > latest:
            latest = str(value)
    return latest


def _provider_result(jobs: dict[str, Any]) -> str:
    if not jobs:
        return "unknown"

    if any(
        isinstance(job, dict) and job.get("last_result") == "error"
        for job in jobs.values()
    ):
        return "error"

    if any(
        isinstance(job, dict) and not job.get("last_end")
        for job in jobs.values()
    ):
        return "unknown"

    return "success"
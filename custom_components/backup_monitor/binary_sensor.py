from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    CONF_STALE_HOURS,
    DEFAULT_STALE_HOURS,
    DOMAIN,
    PROVIDER_BACKREST,
    PROVIDER_DUPLICATI,
)
from .entity import BackupMonitorEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    await coordinator.async_refresh()
    provider = entry.data["provider"]
    stale_hours = int(entry.options.get(CONF_STALE_HOURS, DEFAULT_STALE_HOURS))

    created: set[str] = set()

    entities: list[BinarySensorEntity] = [
        ProviderHealthyBinarySensor(coordinator, provider, stale_hours),
        ProviderStaleBinarySensor(coordinator, provider, stale_hours),
    ]

    async_add_entities(entities)

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


class ProviderHealthyBinarySensor(BackupMonitorEntity, BinarySensorEntity):
    _attr_icon = "mdi:shield-check-outline"

    def __init__(self, coordinator, provider: str, stale_hours: int) -> None:
        super().__init__(coordinator, provider, "_provider_healthy", "Healthy")
        self._stale_hours = stale_hours

    @property
    def is_on(self):
        return _provider_is_healthy(
            self.coordinator.data,
            self._provider,
            self._stale_hours,
        )


class ProviderStaleBinarySensor(BackupMonitorEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:clock-alert-outline"

    def __init__(self, coordinator, provider: str, stale_hours: int) -> None:
        super().__init__(coordinator, provider, "_provider_stale", "Stale")
        self._stale_hours = stale_hours

    @property
    def is_on(self):
        return _provider_is_stale(
            self.coordinator.data,
            self._provider,
            self._stale_hours,
        )


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


def _completed_jobs_for_provider(
    data: dict[str, Any] | None,
    provider: str,
) -> dict[str, dict[str, Any]]:
    jobs = _jobs_for_provider(data, provider)
    completed: dict[str, dict[str, Any]] = {}

    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            continue
        if job.get("last_end"):
            completed[job_id] = job

    return completed


def _provider_is_stale(
    data: dict[str, Any] | None,
    provider: str,
    stale_hours: int,
) -> bool:
    completed_jobs = _completed_jobs_for_provider(data, provider)
    if not completed_jobs:
        return True

    latest_completed: datetime | None = None

    for job in completed_jobs.values():
        value = job.get("last_end")
        if not value:
            continue

        try:
            last = datetime.fromisoformat(value)
        except Exception:
            continue

        if latest_completed is None or last > latest_completed:
            latest_completed = last

    if latest_completed is None:
        return True

    now = dt_util.utcnow()
    return (now - latest_completed) > timedelta(hours=stale_hours)


def _provider_is_healthy(
    data: dict[str, Any] | None,
    provider: str,
    stale_hours: int,
) -> bool:
    completed_jobs = _completed_jobs_for_provider(data, provider)
    if not completed_jobs:
        return False

    if _provider_is_stale(data, provider, stale_hours):
        return False

    for job in completed_jobs.values():
        result = str(job.get("last_result") or "").strip().lower()
        if result in {"error", "failed", "status_error", "status_failed"}:
            return False

    return True
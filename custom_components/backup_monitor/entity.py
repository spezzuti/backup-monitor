from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_PROVIDER, ATTR_JOB_ID


class BackupMonitorEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, provider: str, job_id: str, name: str) -> None:
        super().__init__(coordinator)
        self._provider = provider
        self._job_id = job_id
        self._attr_unique_id = f"{coordinator.entry.entry_id}:{provider}:{job_id}:{self.__class__.__name__}"
        self._attr_name = name

    @property
    def extra_state_attributes(self):
        return {ATTR_PROVIDER: self._provider, ATTR_JOB_ID: self._job_id}

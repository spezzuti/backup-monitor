from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_JOB_ID, ATTR_PROVIDER, DOMAIN


class BackupMonitorEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, provider: str, job_id: str, name: str) -> None:
        super().__init__(coordinator)
        self._provider = provider
        self._job_id = job_id
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}:{provider}:{job_id}:{self.__class__.__name__}"
        )
        self._attr_name = name

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=self.coordinator.entry.title,
            manufacturer="Backup Monitor",
            model=f"{self._provider.capitalize()} Backup Provider",
        )

    @property
    def extra_state_attributes(self):
        return {ATTR_PROVIDER: self._provider, ATTR_JOB_ID: self._job_id}

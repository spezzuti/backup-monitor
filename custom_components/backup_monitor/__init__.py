from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, PLATFORMS
from .coordinator import create_coordinator


async def _async_handle_run_backup(hass: HomeAssistant, call: ServiceCall) -> None:
    entry_id = call.data["entry_id"]
    job_id = call.data["job_id"]

    entry_block = hass.data.get(DOMAIN, {}).get(entry_id)
    if entry_block is None:
        raise HomeAssistantError(f"Unknown Backup Monitor entry_id: {entry_id}")

    coordinator = entry_block["coordinator"]
    client = coordinator.client

    provider = coordinator.entry.data["provider"]
    if provider == "backrest":
        await client.async_run_plan(job_id)
    elif provider == "duplicati":
        await client.async_run_job(job_id)
    else:
        raise HomeAssistantError(f"Unsupported provider: {provider}")

    await coordinator.async_request_refresh()


async def _async_handle_refresh_provider(hass: HomeAssistant, call: ServiceCall) -> None:
    entry_id = call.data["entry_id"]

    entry_block = hass.data.get(DOMAIN, {}).get(entry_id)
    if entry_block is None:
        raise HomeAssistantError(f"Unknown Backup Monitor entry_id: {entry_id}")

    coordinator = entry_block["coordinator"]
    await coordinator.async_request_refresh()


async def _async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, "run_backup"):
        return

    hass.services.async_register(
        DOMAIN,
        "run_backup",
        lambda call: _async_handle_run_backup(hass, call),
    )

    hass.services.async_register(
        DOMAIN,
        "refresh_provider",
        lambda call: _async_handle_refresh_provider(hass, call),
    )


async def _async_unregister_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, "run_backup"):
        hass.services.async_remove(DOMAIN, "run_backup")

    if hass.services.has_service(DOMAIN, "refresh_provider"):
        hass.services.async_remove(DOMAIN, "refresh_provider")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = await create_coordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator

    await _async_register_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    if not hass.data.get(DOMAIN):
        await _async_unregister_services(hass)

    return unloaded
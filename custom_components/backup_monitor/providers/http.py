from __future__ import annotations

from typing import Any

from aiohttp import ClientSession, ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession


def get_session(hass: HomeAssistant, verify_ssl: bool) -> ClientSession:
    if verify_ssl:
        return async_get_clientsession(hass)
    return async_get_clientsession(hass, verify_ssl=False)


DEFAULT_TIMEOUT = ClientTimeout(total=30, connect=10)


async def json_post(
    session: ClientSession,
    url: str,
    payload: dict[str, Any],
    auth=None,
    timeout: ClientTimeout = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    allow_redirects: bool = True,
) -> Any:
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    async with session.post(url, json=payload, auth=auth, timeout=timeout, headers=h, allow_redirects=allow_redirects) as resp:
        resp.raise_for_status()
        if resp.content_type == "application/json":
            return await resp.json()
        return await resp.text()


async def json_get(
    session: ClientSession,
    url: str,
    auth=None,
    timeout: ClientTimeout = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    allow_redirects: bool = True,
) -> Any:
    async with session.get(url, auth=auth, timeout=timeout, headers=headers, allow_redirects=allow_redirects) as resp:
        resp.raise_for_status()
        if resp.content_type == "application/json":
            return await resp.json()
        return await resp.text()

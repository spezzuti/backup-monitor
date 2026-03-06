from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from homeassistant.core import HomeAssistant

from ..const import CONF_BASE_URL, CONF_PASSWORD, CONF_VERIFY_SSL
from .http import get_session, json_get, json_post

_LOGGER = logging.getLogger(__name__)


class DuplicatiClient:
    """Duplicati API client for the observed 2.2.x API behavior."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.base_url: str = str(entry.data[CONF_BASE_URL]).rstrip("/")
        self.password: str = entry.data[CONF_PASSWORD]
        self.verify_ssl: bool = bool(entry.options.get(CONF_VERIFY_SSL, entry.data.get(CONF_VERIFY_SSL, True)))
        self._session = get_session(hass, self.verify_ssl)
        self._access_token: str | None = None

    async def async_validate(self) -> None:
        await self._ensure_bearer()
        backups = await self._get_backups()
        if not backups:
            raise ValueError("Connected to Duplicati but no backups were returned")

    async def async_fetch(self) -> dict[str, Any]:
        await self._ensure_bearer()
        backups = await self._get_backups()

        jobs: dict[str, dict[str, Any]] = {}
        for b in backups:
            if not isinstance(b, dict):
                continue

            jid = str(b.get("ID") or b.get("id") or b.get("Id") or "")
            if not jid:
                continue

            name = b.get("Name") or b.get("name")
            metadata = b.get("Metadata") if isinstance(b.get("Metadata"), dict) else {}

            last_started = _parse_time(
                metadata.get("LastBackupStarted")
                or metadata.get("LastCompactStarted")
                or b.get("LastRunStartTime")
                or b.get("lastRunStartTime")
            )
            last_finished = _parse_time(
                metadata.get("LastBackupFinished")
                or metadata.get("LastBackupDate")
                or metadata.get("LastCompactFinished")
                or b.get("LastRunEndTime")
                or b.get("lastRunEndTime")
            )

            duration_s = _parse_duration_seconds(
                metadata.get("LastBackupDuration")
                or metadata.get("LastCompactDuration")
            )
            if duration_s is None and last_started and last_finished:
                duration_s = (last_finished - last_started).total_seconds()

            last_error = metadata.get("LastErrorMessage")
            last_error_date = metadata.get("LastErrorDate")
            last_result = "success"
            if last_error or last_error_date:
                last_result = "error"

            jobs[jid] = {
                "job_id": jid,
                "name": str(name) if name is not None else None,
                "last_result": last_result,
                "last_end": last_finished.isoformat() if last_finished else None,
                "last_start": last_started.isoformat() if last_started else None,
                "duration_s": duration_s,
                "last_error_message": str(last_error) if last_error is not None else None,
                "last_error_date": str(last_error_date) if last_error_date is not None else None,
            }

        return {"jobs": jobs, "raw": {"job_count": len(jobs)}}

    async def async_run_job(self, job_id: str) -> None:
        await self._ensure_bearer()
        await json_post(
            self._session,
            f"{self.base_url}/api/v1/backup/{job_id}/run",
            {},
            headers=self._auth_headers(),
        )

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token}"} if self._access_token else {}

    async def _ensure_bearer(self) -> None:
        if self._access_token:
            return

        login_data = await json_post(
            self._session,
            f"{self.base_url}/api/v1/auth/login",
            {"password": self.password},
        )
        token = _extract_token(login_data)
        if not token:
            raise ValueError("Duplicati login did not return an access token")
        self._access_token = token

    async def _get_backups(self) -> list[dict[str, Any]]:
        data = await json_get(
            self._session,
            f"{self.base_url}/api/v1/backups",
            headers=self._auth_headers(),
        )

        if isinstance(data, list):
            if len(data) == 1 and isinstance(data[0], list):
                data = data[0]

            if data and isinstance(data[0], dict) and "Backup" in data[0]:
                out: list[dict[str, Any]] = []
                for item in data:
                    if isinstance(item, dict) and isinstance(item.get("Backup"), dict):
                        out.append(item["Backup"])
                return out

            return [b for b in data if isinstance(b, dict)]

        if isinstance(data, dict):
            for key in ("backups", "Backups", "items", "Items", "value", "Value"):
                value = data.get(key)
                if isinstance(value, list):
                    return [b for b in value if isinstance(b, dict)]

            for key in ("data", "Data", "result", "Result"):
                nested = data.get(key)
                if isinstance(nested, dict):
                    for key2 in ("backups", "Backups", "items", "Items", "value", "Value"):
                        value2 = nested.get(key2)
                        if isinstance(value2, list):
                            return [b for b in value2 if isinstance(b, dict)]

        _LOGGER.debug("Unexpected Duplicati /api/v1/backups response: %s", str(data)[:500])
        return []


def _extract_token(data: Any) -> str | None:
    if isinstance(data, dict):
        for key in ("AccessToken", "accessToken", "access_token", "token"):
            value = data.get(key)
            if isinstance(value, str) and value:
                return value
        for key in ("data", "Data", "result", "Result"):
            nested = data.get(key)
            if isinstance(nested, dict):
                token = _extract_token(nested)
                if token:
                    return token
    if isinstance(data, str) and data.strip():
        return data.strip()
    return None


def _parse_time(v: Any) -> datetime | None:
    if not v:
        return None
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception:
            return None
    try:
        n = float(v)
        if n > 1e12:
            n /= 1000.0
        return datetime.fromtimestamp(n, tz=timezone.utc)
    except Exception:
        return None


def _parse_duration_seconds(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        try:
            return float(s)
        except Exception:
            pass
        parts = s.split(":")
        try:
            if len(parts) == 3:
                h = float(parts[0])
                m = float(parts[1])
                sec = float(parts[2])
                return h * 3600 + m * 60 + sec
        except Exception:
            return None
    return None

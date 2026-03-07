from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from aiohttp import BasicAuth
from homeassistant.core import HomeAssistant

from ..const import CONF_BASE_URL, CONF_PASSWORD, CONF_USERNAME, CONF_VERIFY_SSL
from .http import get_session, json_post


@dataclass(frozen=True)
class BackrestPlanState:
    plan_id: str
    last_status: str | None
    last_end: datetime | None
    last_start: datetime | None
    last_message: str | None
    duration_s: float | None


class BackrestClient:
    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.base_url: str = str(entry.data[CONF_BASE_URL]).rstrip("/")
        self.username: str = entry.data[CONF_USERNAME]
        self.password: str = entry.data[CONF_PASSWORD]
        self.verify_ssl: bool = bool(entry.options.get(CONF_VERIFY_SSL, entry.data.get(CONF_VERIFY_SSL, True)))

        self._session = get_session(hass, self.verify_ssl)
        self._auth = BasicAuth(self.username, self.password)

    async def async_validate(self) -> None:
        await self._get_operations()

    async def async_fetch(self) -> dict[str, Any]:
        data = await self._get_operations()
        ops = []
        if isinstance(data, dict) and isinstance(data.get("operations"), list):
            ops = data["operations"]

        plans: dict[str, BackrestPlanState] = {}

        latest_any: dict[str, BackrestPlanState] = {}
        latest_terminal: dict[str, BackrestPlanState] = {}
        latest_success: dict[str, BackrestPlanState] = {}

        for op in ops:
            if not isinstance(op, dict):
                continue

            pid = op.get("planId") or op.get("plan_id")
            if not pid:
                continue

            plan_id = str(pid)
            st = _parse_operation(plan_id, op)
            st_ts = st.last_end or st.last_start

            prev_any = latest_any.get(plan_id)
            prev_any_ts = (prev_any.last_end or prev_any.last_start) if prev_any else None
            if prev_any is None or (st_ts and (prev_any_ts is None or st_ts > prev_any_ts)):
                latest_any[plan_id] = st

            if not _is_pending_status(st.last_status):
                prev_terminal = latest_terminal.get(plan_id)
                prev_terminal_ts = (prev_terminal.last_end or prev_terminal.last_start) if prev_terminal else None
                if prev_terminal is None or (st_ts and (prev_terminal_ts is None or st_ts > prev_terminal_ts)):
                    latest_terminal[plan_id] = st

            if _is_success_status(st.last_status):
                prev_success = latest_success.get(plan_id)
                prev_success_ts = (prev_success.last_end or prev_success.last_start) if prev_success else None
                if prev_success is None or (st_ts and (prev_success_ts is None or st_ts > prev_success_ts)):
                    latest_success[plan_id] = st

        for plan_id, st_any in latest_any.items():
            chosen = latest_terminal.get(plan_id, st_any)
            success_state = latest_success.get(plan_id)

            if success_state is not None:
                chosen = BackrestPlanState(
                    plan_id=chosen.plan_id,
                    last_status=chosen.last_status,
                    last_end=success_state.last_end,
                    last_start=success_state.last_start,
                    last_message=chosen.last_message,
                    duration_s=success_state.duration_s,
                )

            plans[plan_id] = chosen

        return {"plans": {pid: _as_dict(s) for pid, s in plans.items()}, "raw": {"operation_count": len(ops)}}

    async def async_run_plan(self, plan_id: str) -> None:
        await json_post(self._session, f"{self.base_url}/v1.Backrest/Backup", {"value": plan_id}, auth=self._auth)

    async def _get_operations(self) -> Any:
        return await json_post(self._session, f"{self.base_url}/v1.Backrest/GetOperations", {"selector": {}}, auth=self._auth)


def _as_dict(st: BackrestPlanState) -> dict[str, Any]:
    return {
        "plan_id": st.plan_id,
        "last_status": st.last_status,
        "last_end": st.last_end.isoformat() if st.last_end else None,
        "last_start": st.last_start.isoformat() if st.last_start else None,
        "last_message": st.last_message,
        "duration_s": st.duration_s,
    }


def _parse_ms_epoch(v: Any) -> datetime | None:
    try:
        if v is None:
            return None
        n = float(v)
        if n > 1e12:
            n /= 1000.0
        return datetime.fromtimestamp(n, tz=UTC)
    except Exception:
        return None

def _normalize_status(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip().lower()


def _is_pending_status(value: Any) -> bool:
    status = _normalize_status(value)
    return status in {
        "status_pending",
        "pending",
        "queued",
        "status_queued",
        "running",
        "status_running",
        "in_progress",
        "status_in_progress",
    }


def _is_success_status(value: Any) -> bool:
    status = _normalize_status(value)
    return status in {
        "success",
        "status_success",
        "completed",
        "status_completed",
        "ok",
    }

def _parse_operation(plan_id: str, op: dict[str, Any]) -> BackrestPlanState:
    status = op.get("status") or op.get("result") or op.get("state")
    msg = op.get("displayMessage") or op.get("message") or op.get("display_message")

    start = _parse_ms_epoch(op.get("unixTimeStartMs") or op.get("startTimeMs") or op.get("start"))
    end = _parse_ms_epoch(op.get("unixTimeEndMs") or op.get("endTimeMs") or op.get("end") or op.get("stopTimeMs"))

    duration_s = (end - start).total_seconds() if start and end else None

    return BackrestPlanState(
        plan_id=plan_id,
        last_status=str(status) if status is not None else None,
        last_end=end,
        last_start=start,
        last_message=str(msg) if msg is not None else None,
        duration_s=duration_s,
    )

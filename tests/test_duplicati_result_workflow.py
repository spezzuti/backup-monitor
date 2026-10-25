"""Synthetic API responses through the provider and provider aggregate helpers.

Uses the repository's normal Home Assistant imports, not module shims.
This is not an integration/startup test against a running HA or Duplicati server.
"""
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock
from urllib.parse import quote

import pytest

from custom_components.backup_monitor import binary_sensor, sensor
from custom_components.backup_monitor.providers import duplicati

CASES = json.loads(
    (Path(__file__).parent / "fixtures/duplicati/backup_result_cases.json").read_text()
)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
async def test_result_workflow(case, monkeypatch):
    client = object.__new__(duplicati.DuplicatiClient)
    client._session = object()
    client.base_url = "https://synthetic.invalid"
    client._access_token = "synthetic-test-token"
    client._ensure_bearer = AsyncMock()
    job_id = case.get("job_id", "synthetic")
    client._get_backups = AsyncMock(return_value=[{
        "ID": job_id, "Name": "Synthetic job", "Metadata": case["metadata"],
    }])
    response = AsyncMock(side_effect=TimeoutError()) if case["network_timeout"] else AsyncMock(return_value=case["logs"])
    monkeypatch.setattr(duplicati, "json_get", response)
    monkeypatch.setattr(binary_sensor.dt_util, "utcnow", lambda: datetime(2026, 10, 22, 2, tzinfo=UTC))

    data = await client.async_fetch()
    job = data["jobs"][job_id]
    expected = case["expected"]
    assert job["last_result"] == expected
    assert sensor._provider_result(data["jobs"], "duplicati") == expected
    assert binary_sensor._provider_is_healthy(data, "duplicati", 36) == (expected == "success")
    assert len(sensor._failed_jobs(data["jobs"])) == (expected == "error")
    assert len(sensor._successful_jobs(data["jobs"])) == (expected == "success")
    assert job["last_error_message"] == case["metadata"].get("LastErrorMessage")
    assert job["last_error_date"] == case["metadata"].get("LastErrorDate")
    response.assert_awaited_once_with(
        client._session,
        f"https://synthetic.invalid/api/v1/backup/{quote(job_id, safe='')}/log?pagesize=100",
        headers=client._auth_headers(),
    )


def test_mixed_unknown_is_not_healthy():
    data = {"jobs": {"a": {"last_result": "success", "last_end": "2026-10-22T01:06:38+00:00"}, "b": {"last_result": "unknown", "last_end": "2026-10-22T01:06:38+00:00"}}}
    assert sensor._provider_result(data["jobs"], "duplicati") == "unknown"
    assert not binary_sensor._provider_is_healthy(data, "duplicati", 36)


def test_backrest_unchanged(monkeypatch):
    monkeypatch.setattr(binary_sensor.dt_util, "utcnow", lambda: datetime(2026, 10, 22, 2, tzinfo=UTC))
    data = {"plans": {"a": {"last_result": "status_success", "last_end": "2026-10-22T01:06:38+00:00"}}}
    assert sensor._provider_result(data["plans"], "backrest") == "success"
    assert binary_sensor._provider_is_healthy(data, "backrest", 36)

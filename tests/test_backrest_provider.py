import json
from pathlib import Path

from custom_components.backup_monitor.providers.backrest import _parse_operation


def test_backrest_parse_operation_success():
    fixture_path = Path("tests/fixtures/backrest/get_operations_success.json")
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    operation = payload["operations"][0]
    state = _parse_operation(operation["planId"], operation)

    assert state.plan_id == "truenas-dockerconfigs"
    assert state.last_status == "success"
    assert state.last_message == "Backup completed"
    assert state.last_start is not None
    assert state.last_end is not None
    assert state.duration_s == 300.0
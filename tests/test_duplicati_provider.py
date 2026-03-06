import json
from pathlib import Path

from custom_components.backup_monitor.providers.duplicati import (
    _extract_token,
    _parse_duration_seconds,
)


def test_duplicati_extract_access_token():
    fixture_path = Path("tests/fixtures/duplicati/login_access_token.json")
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    token = _extract_token(payload)

    assert token == "test-access-token"


def test_duplicati_parse_duration_seconds_hhmmss():
    assert _parse_duration_seconds("00:02:00") == 120.0


def test_duplicati_wrapped_backup_metadata_shape():
    fixture_path = Path("tests/fixtures/duplicati/backups_wrapped_metadata.json")
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert isinstance(payload, list)
    assert "Backup" in payload[0]

    backup = payload[0]["Backup"]
    metadata = backup["Metadata"]

    assert backup["ID"] == "1"
    assert backup["Name"] == "docker-config-backup"
    assert metadata["LastBackupFinished"] == "2026-03-05T12:00:00Z"
    assert metadata["LastBackupDuration"] == "00:02:00"
    assert metadata["LastErrorMessage"] is None

def test_duplicati_extract_token_missing():
    payload = {}

    token = _extract_token(payload)

    assert token is None
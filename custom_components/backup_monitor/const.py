from __future__ import annotations

DOMAIN = "backup_monitor"
PLATFORMS: list[str] = ["sensor", "binary_sensor", "button"]

CONF_PROVIDER = "provider"
PROVIDER_BACKREST = "backrest"
PROVIDER_DUPLICATI = "duplicati"

CONF_BASE_URL = "base_url"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_VERIFY_SSL = "verify_ssl"
CONF_POLL_INTERVAL = "poll_interval"
CONF_STALE_HOURS = "stale_hours"

DEFAULT_VERIFY_SSL = True
DEFAULT_POLL_INTERVAL = 60  # seconds
DEFAULT_STALE_HOURS = 36

ATTR_PROVIDER = "provider"
ATTR_JOB_ID = "job_id"

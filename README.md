<p align="center">
  <img src="logo.png" width="200">
</p>

# Backup Monitor

Backup Monitor is a Home Assistant custom integration for monitoring backup jobs from:

- Backrest
- Duplicati

It exposes backup status, timing, stale state, and run-now actions in Home Assistant.

---

## Current status
Early HACS-prep release track. Use internal/LAN endpoints for provider APIs.

---

## Recommended architecture

Home Assistant should talk to internal hostnames such as:

- `https://backrest.lan`
- `https://duplicati.lan`

Do not place Cloudflare or other CDN/WAF layers in front of the API endpoints used by Home Assistant.  
Self-signed/internal TLS may require **Verify TLS Off**.

---

## Installation

### HACS (Recommended)

1. Open **HACS** in Home Assistant
2. Go to **Integrations**
3. Click the **⋮ (top right)** → **Custom repositories**
4. Add:

https://github.com/spezzuti/backup-monitor

5. Category: **Integration**
6. Click **Add**
7. Search for **Backup Monitor**
8. Install and **Restart Home Assistant**

---

### Manual

1. Copy:

custom_components/backup_monitor

into your Home Assistant config directory:

/config/custom_components/backup_monitor

2. Restart Home Assistant

---

## Configuration

After installation:

1. Go to **Settings → Devices & Services**
2. Click **+ Add Integration**
3. Search for **Backup Monitor**

---

### Backrest Configuration

- **Host**  
URL to your Backrest instance  
Example:

http://192.168.1.100:9898


- **Password**  
Your Backrest web UI password

- **Verify TLS**  
Enable only if using valid HTTPS  
Disable for self-signed certs or internal domains

---

### Duplicati Configuration

- **Host**  
URL to your Duplicati instance  
Example:

http://192.168.1.100:8200


- **Password**  
Your Duplicati web UI password

- **Verify TLS**  
Same behavior as above

---

## Features

- Config flow (UI-based setup)
- Backrest support
- Duplicati support
- Run-now buttons
- Last result / success / duration sensors
- Stale binary sensors

---

## Entities Created

Depending on the provider, Backup Monitor creates:

### Sensors
- Last backup result
- Last run time
- Duration
- Backup status

### Binary Sensors
- Stale backup detection
- Success / failure state

### Buttons
- Trigger backup job manually

---

## Usage

Once configured:

- Add sensors to your dashboard
- Use buttons to trigger backups
- Create automations such as:
- Alert on backup failure
- Notify if backup hasn’t run in X hours
- Monitor long-running jobs

---

## Troubleshooting

- Always restart Home Assistant after install
- If integration does not appear:
- Clear browser cache
- Confirm files exist in:
  ```
  /config/custom_components/backup_monitor/
  ```
- Check logs:

Settings → System → Logs


---

## Development

### Local setup

Create a Python virtual environment and install development dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_dev.txt

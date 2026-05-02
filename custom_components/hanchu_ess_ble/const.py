from __future__ import annotations

DOMAIN = "hanchu_ess_ble"

# BLE UUIDs (from web app)
BLE_SERVICE_UUID = "0000ffff-0000-1000-8000-00805f9b34fb"
BLE_SERVICE_UUID_FALLBACK = "0000ff00-0000-1000-8000-00805f9b34fb"
BLE_NOTIFY_CHAR_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"
BLE_WRITE_CHAR_UUID = "0000ff02-0000-1000-8000-00805f9b34fb"

# Work mode mapping (P651 / L019)
WORK_MODE_MAP = {
    "self_use": 1,       # Self-Consumption
    "backup": 2,         # Backup
    "time_of_use": 3,    # User-Defined / TOU
    "off_grid": 4,       # Off-Grid
}
WORK_MODE_MAP_INV = {v: k for k, v in WORK_MODE_MAP.items()}

# Seconds in a day
SECONDS_PER_DAY = 86400

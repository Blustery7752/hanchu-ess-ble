# Hanchu ESS BLE PG

Local Bluetooth Low Energy (BLE) integration for **Hanchu ESS inverters**, providing real‑time telemetry and control directly from Home Assistant — no cloud, no Wi‑Fi dongle, no internet required.

This is a modern, coordinator‑based Home Assistant integration built from the ground up for stability, correctness, and full BLE protocol support.

---

## 🚀 Features

### ✔ Local BLE connection  
Connects directly to the inverter’s onboard Bluetooth module.

### ✔ Automatic Bluetooth discovery  
Detects supported inverters broadcasting names such as:

- `HC:L110`
- `HC:L112`
- `HC:L113`
- `HC:L114`
- `HC:L115`
- `HC:L120`
- `HC:L122`

### ✔ Full coordinator architecture  
- Single BLE connection  
- Centralised polling  
- All entities updated atomically  
- Correct availability handling  
- Clean device registry integration  

### ✔ Sensor coverage  
Includes (model‑dependent):

- Battery SoC  
- Battery temperature  
- Battery charge/discharge power  
- PV1 / PV2 voltage & current  
- PV energy today / total  
- Grid voltage / current / frequency  
- EPS voltage / current / frequency  
- EPS active power  
- Inverter temperature  
- BLE RSSI  
- Many diagnostic registers  

### ✔ Writable entities  
Supports inverter configuration via BLE:

- Numeric settings (e.g., SOC limits, charge windows)  
- Select options (e.g., work mode)  

### ✔ No cloud, no internet  
Everything is local.

---

## ⚠️ Bluetooth Requirements

### Home Assistant OS users  
Many mini‑PC onboard Bluetooth chipsets **do not expose DBus advertisement events**, meaning HA’s Bluetooth integration cannot see BLE devices even though the hardware works.

If:

- Bluetooth Visualisation sees the inverter  
- but  
- Home Assistant → Settings → Bluetooth shows **no devices**

…then your hardware is not compatible with HAOS’s Bluetooth stack.

### ✔ Recommended solution: **ESP32 Bluetooth Proxy**  
This integration works flawlessly with an ESP32 proxy.

Supported devices:

- **M5Stack Atom Lite** (recommended)  
- ESP32‑DevKitC / ESP32‑WROOM boards  

Flash using the official HA firmware:

https://www.home-assistant.io/esp32/

Once added, HA will immediately detect the inverter.

---

## 📦 Installation

### HACS (recommended)

1. Open HACS → Integrations  
2. Menu → Custom repositories  
3. Add your repo URL  
4. Category: **Integration**  
5. Install  
6. Restart Home Assistant  

### Manual

1. Copy `custom_components/hanchu_ess_ble` into your HA `custom_components` folder  
2. Restart Home Assistant  

---

## 🛠 Setup

1. Ensure Bluetooth is working (or add an ESP32 proxy)  
2. Bring the inverter into BLE range  
3. Go to **Settings → Devices & Services**  
4. Add **Hanchu ESS BLE**  
5. Select the discovered inverter  
6. Done  

---

## 📊 Sensors

This integration exposes a wide range of inverter telemetry.  
Some sensors are enabled by default; others can be enabled manually.

Examples:

- Battery SoC  
- Battery temperature  
- Battery charge/discharge power  
- PV1/PV2 voltage & current  
- PV energy today / total  
- Grid frequency  
- EPS voltage / current / frequency  
- EPS active power  
- Inverter temperature  
- BLE RSSI  

Scaling and units are continuously refined based on field data.

---

## 🔧 Writable Entities

Depending on inverter model, the integration supports:

- Charge/discharge SOC limits  
- Charge windows  
- Work mode selection  
- Other numeric configuration registers  

These appear as **Number** and **Select** entities.

---

## 🧩 Architecture Overview

This integration uses:

- `ble_client.py` — BLE transport  
- `protocol.py` — frame parsing & register decoding  
- `coordinator.py` — centralised polling  
- `entity.py` — base entity class  
- `sensor.py` — telemetry sensors  
- `number.py` — writable numeric settings  
- `select.py` — mode selectors  
- `config_flow.py` — UI setup & discovery  
- `manifest.json` — Bluetooth matchers  

This is a full, modern HA integration — not a prototype.

---

## 🐞 Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.hanchu_ess_ble: debug

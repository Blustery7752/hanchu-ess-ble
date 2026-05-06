from __future__ import annotations

import json
import logging
import random
import string
from typing import Dict, Any, Optional

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

_LOGGER = logging.getLogger(__name__)


class HanchuProtocol:
    """AES key exchange, decryption, telemetry parsing, and write command builder."""

    BASE_KEY = "gxkj@2099@1914zy"
    BASE_IV = "9z64Qr8mZH7Pg8d1"

    FRIENDLY_MAP = {
        # PV
        "P024": "pv1_voltage",
        "P025": "pv1_current",
        "P026": "pv2_voltage",
        "P027": "pv2_current",
        "P060": "pv_power_total",
        "P061": "pv_energy_today",
        "P062": "pv_energy_total",

        # Grid
        "P044": "grid_voltage",
        "P045": "grid_current",
        "P053": "grid_frequency",
        "P055": "grid_power",
        "P056": "grid_reactive_power",
        "P057": "grid_power_factor",
        "P638": "grid_import_today",
        "P639": "grid_export_today",
        "P500": "grid_power_state",

        # Battery
        "P067": "battery_voltage",
        "P068": "battery_current",
        "P069": "battery_power",
        "P070": "battery_temperature",
        "P071": "battery_soc",
        "P075": "battery_charge_today",
        "P076": "battery_discharge_today",

        # Load
        "P644": "load_power",

        # Identity
        "P002": "inverter_serial",
        "P006": "inverter_firmware",
        "L023": "dtu_firmware",

        # Work mode / SOC
        "P651": "work_mode",
        "P647": "charge_to_soc",
        "P648": "discharge_to_soc",
        "P772": "min_soc_cutoff",

        # Charge/discharge windows
        "L005": "charge_p1_start",
        "L006": "charge_p1_end",
        "L007": "charge_p2_start",
        "L008": "charge_p2_end",
        "L009": "charge_p3_start",
        "L010": "charge_p3_end",
        "L011": "discharge_p1_start",
        "L012": "discharge_p1_end",
        "L013": "discharge_p2_start",
        "L014": "discharge_p2_end",
        "L015": "discharge_p3_start",
        "L016": "discharge_p3_end",

        # Power limits
        "L017": "charge_power_limit",
        "L018": "discharge_power_limit",
        "L074": "max_soc_limit",
    }

    def __init__(self) -> None:
        self._dynamic_key: Optional[bytes] = None

    # ------------------------------------------------------------------ #
    # Key exchange (renamed for ble_client.py)
    # ------------------------------------------------------------------ #

    def build_random_fix(self) -> bytes:
        """Generate randomFix, derive dynamic key, and build 0x05 packet."""
        chars = string.ascii_letters + string.digits
        random_fix = "".join(random.choice(chars) for _ in range(6))
        _LOGGER.debug("Generated random fix: %s", random_fix)

        self._dynamic_key = self._derive_dynamic_key(random_fix)

        packet = bytearray(7)
        packet[0] = 0x05
        packet[1:7] = random_fix.encode("utf-8")
        return bytes(packet)

    def _derive_dynamic_key(self, fix: str) -> bytes:
        """Original Hanchu dynamic key algorithm (unchanged)."""
        if len(fix) != 6:
            _LOGGER.error("randomFix must be exactly 6 characters")
            return self.BASE_KEY.encode("utf-8")[:16]

        offset = ord(fix[5]) % 10
        key_arr = list(self.BASE_KEY)
        for i in range(6):
            if offset + i < len(key_arr):
                key_arr[offset + i] = fix[i]

        dyn_key = "".join(key_arr).encode("utf-8")[:16]
        _LOGGER.debug("Dynamic key generated (offset=%d)", offset)
        return dyn_key

    # ------------------------------------------------------------------ #
    # AES‑CFB8 decrypt / encrypt
    # ------------------------------------------------------------------ #

    def _decrypt(self, encrypted: bytes) -> Optional[bytes]:
        if not self._dynamic_key:
            _LOGGER.error("No dynamic key set; random fix packet not sent yet")
            return None

        iv = self.BASE_IV.encode("utf-8")[:16]
        cipher = Cipher(algorithms.AES(self._dynamic_key), modes.CFB8(iv))
        decryptor = cipher.decryptor()

        try:
            return decryptor.update(encrypted) + decryptor.finalize()
        except Exception as err:
            _LOGGER.error("AES decrypt error: %s", err)
            return None

    def encrypt_command(self, plaintext: bytes) -> bytes:
        """Encrypt JSON write frame using AES‑128‑CFB8."""
        if not self._dynamic_key:
            raise RuntimeError("No dynamic key set; random fix packet not sent yet")

        iv = self.BASE_IV.encode("utf-8")[:16]
        cipher = Cipher(algorithms.AES(self._dynamic_key), modes.CFB8(iv))
        encryptor = cipher.encryptor()
        return encryptor.update(plaintext) + encryptor.finalize()

    # ------------------------------------------------------------------ #
    # Notification parsing
    # ------------------------------------------------------------------ #

    def parse_notification(self, encrypted: bytes) -> Dict[str, Any]:
        if not encrypted:
            return {}

        decrypted = self._decrypt(encrypted)
        if decrypted is None:
            return {}

        # LOCAL MODE
        if decrypted[0] == 0x03:
            if len(decrypted) < 6:
                _LOGGER.warning("LOCAL frame too short")
                return {}
            length = decrypted[4] | (decrypted[5] << 8)
            json_bytes = decrypted[6:6 + length]
            json_str = json_bytes.decode("utf-8", errors="ignore").strip("\x00").strip()
        else:
            # STANDARD MODE
            json_str = decrypted.decode("utf-8", errors="ignore").strip("\x00").strip()

        if not json_str:
            return {}

        try:
            parsed = json.loads(json_str)
        except Exception as err:
            _LOGGER.error("JSON decode error: %s | payload=%r", err, json_str)
            return {}

        items = parsed.get("data", [])
        if not isinstance(items, list):
            return {}

        result: Dict[str, Any] = {}
        for item in items:
            code = item.get("k")
            raw_val = item.get("v")
            if code is None:
                continue

            friendly = self.FRIENDLY_MAP.get(code)
            if friendly:
                result[friendly] = self._convert_value(raw_val)

        return result

    # ------------------------------------------------------------------ #
    # Write command builders (required by ble_client.py)
    # ------------------------------------------------------------------ #

    def _build_json_command(self, code: str, value: Any) -> bytes:
        payload = {
            "tid": "10001",
            "act": "2",
            "data": [{"k": code, "v": value}],
        }
        return json.dumps(payload, separators=(",", ":")).encode("utf-8")

    def build_set_work_mode(self, mode: str) -> bytes:
        return self._build_json_command("P651", mode)

    def build_set_charge_power_limit(self, watts: int) -> bytes:
        return self._build_json_command("L017", watts)

    def build_set_discharge_power_limit(self, watts: int) -> bytes:
        return self._build_json_command("L018", watts)

    def build_set_max_soc(self, soc: int) -> bytes:
        return self._build_json_command("L074", soc)

    def build_set_charge_to_soc(self, soc: int) -> bytes:
        return self._build_json_command("P647", soc)

    def build_set_discharge_to_soc(self, soc: int) -> bytes:
        return self._build_json_command("P648", soc)

    def build_set_min_soc(self, soc: int) -> bytes:
        return self._build_json_command("P772", soc)

    def build_set_battery_preheat_auto(self, flag: int) -> bytes:
        return self._build_json_command("L108", flag)

    def build_set_battery_preheat_manual(self, flag: int) -> bytes:
        return self._build_json_command("L114", flag)

    def build_set_meter_type(self, meter_type: int) -> bytes:
        return self._build_json_command("L034", meter_type)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _convert_value(v: Any) -> Any:
        if isinstance(v, (int, float)):
            return v
        if isinstance(v, str):
            try:
                return float(v) if "." in v else int(v)
            except ValueError:
                return v
        return v

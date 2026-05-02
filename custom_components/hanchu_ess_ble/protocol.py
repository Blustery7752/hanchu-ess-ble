from __future__ import annotations

import json
import logging
import random
import string
from typing import Dict, Any, Optional

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

_LOGGER = logging.getLogger(__name__)


class HanchuProtocol:
    """AES key exchange, decryption, and telemetry parsing."""

    # Must match web app
    BASE_KEY = "gxkj@2099@1914zy"
    BASE_IV = "9z64Qr8mZH7Pg8d1"

    # P/L/B → friendly names
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

        # Battery (inverter-side)
        "P067": "battery_voltage",
        "P068": "battery_current",
        "P069": "battery_power",
        "P070": "battery_temperature",
        "P071": "battery_soc",  # decimal 0.67 = 67%
        "P075": "battery_charge_today",
        "P076": "battery_discharge_today",

        # Load
        "P644": "load_power",

        # Identity
        "P002": "inverter_serial",
        "P006": "inverter_firmware",
        "L023": "dtu_firmware",

        # Work mode / SOC limits
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
    # Key exchange (random fix packet)
    # ------------------------------------------------------------------ #

    def build_random_fix_packet(self) -> bytes:
        """Generate randomFix, derive dynamic key, and build 0x05 packet."""
        chars = string.ascii_letters + string.digits
        random_fix = "".join(random.choice(chars) for _ in range(6))
        _LOGGER.debug("Generated random fix: %s", random_fix)

        self._dynamic_key = self._derive_dynamic_key(random_fix)

        fix_bytes = random_fix.encode("utf-8")
        packet = bytearray(7)
        packet[0] = 0x05
        packet[1:1 + 6] = fix_bytes
        return bytes(packet)

    def _derive_dynamic_key(self, fix: str) -> bytes:
        """Same logic as JS AESHelper.generateDynamicKey."""
        if len(fix) != 6:
            _LOGGER.error("randomFix must be exactly 6 characters")
            return self.BASE_KEY.encode("utf-8")[:16]

        offset = ord(fix[5]) % 10
        key_arr = list(self.BASE_KEY)
        for i in range(6):
            if offset + i < len(key_arr):
                key_arr[offset + i] = fix[i]
        dyn_key_str = "".join(key_arr)
        _LOGGER.debug("Dynamic key generated (offset=%d)", offset)
        return dyn_key_str.encode("utf-8")[:16]

    # ------------------------------------------------------------------ #
    # AES‑CFB8 decryption
    # ------------------------------------------------------------------ #

    def _decrypt(self, encrypted: bytes) -> Optional[bytes]:
        """Decrypt encrypted notification using AES‑128‑CFB8."""
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

    # ------------------------------------------------------------------ #
    # Public entrypoint: encrypted bytes → friendly telemetry
    # ------------------------------------------------------------------ #

    def parse_notification(self, encrypted: bytes) -> Dict[str, Any]:
        """Parse encrypted BLE notification into friendly telemetry dict."""
        if not encrypted:
            return {}

        decrypted = self._decrypt(encrypted)
        if decrypted is None:
            return {}

        # LOCAL MODE framing
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
            _LOGGER.warning("Empty JSON payload")
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

            val = self._convert_value(raw_val)
            friendly = self.FRIENDLY_MAP.get(code)
            if friendly:
                result[friendly] = val

        return result

    @staticmethod
    def _convert_value(v: Any) -> Any:
        """Convert numeric strings to float/int."""
        if isinstance(v, (int, float)):
            return v
        if isinstance(v, str):
            try:
                if "." in v:
                    return float(v)
                return int(v)
            except ValueError:
                return v
        return v

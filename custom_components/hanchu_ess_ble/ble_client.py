from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional

from bleak import BleakClient

from .protocol import HanchuProtocol
from .const import (
    BLE_NOTIFY_CHAR_UUID,
    BLE_WRITE_CHAR_UUID,
    WORK_MODE_MAP,
)

_LOGGER = logging.getLogger(__name__)


class HanchuBleClient:
    """Handles BLE connection, AES handshake, notifications, and write commands."""

    def __init__(self, hass, entry, address: str):
        self.hass = hass
        self.entry = entry
        self.address = address

        self._client: Optional[BleakClient] = None
        self._protocol = HanchuProtocol()
        self._notify_callback: Optional[Callable[[Dict[str, Any]], None]] = None

        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ #
    # Connection handling
    # ------------------------------------------------------------------ #

    async def connect(self) -> None:
        """Ensure BLE connection is established and AES key exchange done."""
        if self._client and self._client.is_connected:
            return

        _LOGGER.info("Connecting to Hanchu inverter at %s", self.address)
        self._client = BleakClient(self.address)

        try:
            await self._client.connect()
            _LOGGER.info("Connected to Hanchu inverter")

            # Subscribe to notifications
            await self._client.start_notify(
                BLE_NOTIFY_CHAR_UUID,
                self._handle_notification,
            )

            # Send random-fix packet to establish dynamic AES key
            random_fix_packet = self._protocol.build_random_fix_packet()
            await self._client.write_gatt_char(
                BLE_WRITE_CHAR_UUID,
                random_fix_packet,
                response=True,
            )
            _LOGGER.debug("Sent random fix packet")

        except Exception as err:
            _LOGGER.error("BLE connection failed: %s", err)
            raise

    async def disconnect(self) -> None:
        """Disconnect BLE client."""
        if self._client and self._client.is_connected:
            await self._client.disconnect()
            _LOGGER.info("Disconnected from Hanchu inverter")

    # ------------------------------------------------------------------ #
    # Notification handling
    # ------------------------------------------------------------------ #

    def set_notification_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Set callback to receive parsed telemetry."""
        self._notify_callback = callback

    def _handle_notification(self, sender: int, data: bytearray):
        """Raw BLE notification → decrypted JSON → friendly telemetry → callback."""
        try:
            parsed = self._protocol.parse_notification(bytes(data))
            if parsed and self._notify_callback:
                self._notify_callback(parsed)
        except Exception as err:
            _LOGGER.error("Failed to handle notification: %s", err)

    # ------------------------------------------------------------------ #
    # Low-level write
    # ------------------------------------------------------------------ #

    async def _write(self, frame: bytes) -> None:
        """Write a raw encrypted frame to the inverter."""
        async with self._lock:
            await self.connect()
            _LOGGER.debug("Writing encrypted frame: %s", frame.hex())
            await self._client.write_gatt_char(
                BLE_WRITE_CHAR_UUID,
                frame,
                response=True,
            )

    # ------------------------------------------------------------------ #
    # JSON write frame builder
    # ------------------------------------------------------------------ #

    def _build_write_frame(self, code: str, value: Any) -> bytes:
        """Build a JSON write frame and encrypt it."""
        payload = {
            "tid": "10001",
            "act": "2",  # write
            "data": [{"k": code, "v": value}],
        }

        json_str = json.dumps(payload, separators=(",", ":"))
        json_bytes = json_str.encode("utf-8")

        encrypted = self._protocol.encrypt(json_bytes)
        if encrypted is None:
            raise RuntimeError("AES encryption failed")

        return encrypted

    async def _write_param(self, code: str, value: Any) -> None:
        """Encrypt and send a write frame."""
        frame = self._build_write_frame(code, value)
        await self._write(frame)

    # ------------------------------------------------------------------ #
    # High-level write operations
    # ------------------------------------------------------------------ #

    async def async_set_work_mode(self, mode: str) -> None:
        """Set inverter work mode (P651)."""
        value = WORK_MODE_MAP[mode]
        await self._write_param("P651", value)

    async def async_set_charge_power_limit(self, watts: int) -> None:
        await self._write_param("L017", watts)

    async def async_set_discharge_power_limit(self, watts: int) -> None:
        await self._write_param("L018", watts)

    async def async_set_max_soc(self, percent: int) -> None:
        await self._write_param("L074", percent)

    async def async_set_charge_to_soc(self, percent: int) -> None:
        await self._write_param("P647", percent)

    async def async_set_discharge_to_soc(self, percent: int) -> None:
        await self._write_param("P648", percent)

    async def async_set_min_soc(self, percent: int) -> None:
        await self._write_param("P772", percent)

    async def async_set_meter_type(self, code: int) -> None:
        await self._write_param("L034", code)

    async def async_set_battery_preheat_auto(self, flag: int) -> None:
        await self._write_param("L108", flag)

    async def async_set_battery_preheat_manual(self, flag: int) -> None:
        await self._write_param("L114", flag)

    # ------------------------------------------------------------------ #
    # Charge/discharge window setters (optional)
    # ------------------------------------------------------------------ #

    async def async_set_charge_window(self, window: str, start: int, end: int) -> None:
        """Set a charge window (seconds after midnight)."""
        mapping = {
            "period_1": ("L005", "L006"),
            "period_2": ("L007", "L008"),
            "period_3": ("L009", "L010"),
        }
        start_code, end_code = mapping[window]
        await self._write_param(start_code, start)
        await self._write_param(end_code, end)

    async def async_set_discharge_window(self, window: str, start: int, end: int) -> None:
        """Set a discharge window (seconds after midnight)."""
        mapping = {
            "period_1": ("L011", "L012"),
            "period_2": ("L013", "L014"),
            "period_3": ("L015", "L016"),
        }
        start_code, end_code = mapping[window]
        await self._write_param(start_code, start)
        await self._write_param(end_code, end)

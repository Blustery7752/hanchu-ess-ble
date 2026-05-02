from __future__ import annotations

import asyncio
import logging
from datetime import time
from typing import Optional, Callable, Dict, Any

from bleak import BleakClient

from .protocol import HanchuProtocol
from .const import (
    BLE_NOTIFY_CHAR_UUID,
    BLE_WRITE_CHAR_UUID,
)

_LOGGER = logging.getLogger(__name__)


class HanchuBleClient:
    """Handles BLE connection + AES handshake + read/write for Hanchu inverter."""

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
        """Ensure BLE connection is established and key exchange done."""
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
        """Write a raw frame to the inverter."""
        async with self._lock:
            await self.connect()
            _LOGGER.debug("Writing frame: %s", frame.hex())
            await self._client.write_gatt_char(
                BLE_WRITE_CHAR_UUID,
                frame,
                response=True,
            )

    # ------------------------------------------------------------------ #
    # High-level operations (called by services + number/select entities)
    # ------------------------------------------------------------------ #

    async def async_set_work_mode(self, mode: str) -> None:
        """Set inverter work mode (you'll implement frame build later)."""
        # Placeholder: build JSON command and encrypt via protocol if you want symmetry
        _LOGGER.debug("Requested work mode change to %s (not yet implemented)", mode)

    async def async_set_charge_window(
        self,
        window: str,
        start_time: time,
        end_time: time,
        enabled: bool,
    ) -> None:
        """Set a charge window (period_1 / period_2 / period_3)."""
        _LOGGER.debug(
            "Requested charge window %s %s-%s enabled=%s (write path TBD)",
            window,
            start_time,
            end_time,
            enabled,
        )

    async def async_set_min_soc(self, value: int) -> None:
        _LOGGER.debug("Requested min SOC set to %s (write path TBD)", value)

    async def async_set_max_soc(self, value: int) -> None:
        _LOGGER.debug("Requested max SOC set to %s (write path TBD)", value)

    async def async_set_grid_charge_limit(self, value: int) -> None:
        _LOGGER.debug("Requested grid charge limit set to %s (write path TBD)", value)

    # ------------------------------------------------------------------ #
    # Polling (optional)
    # ------------------------------------------------------------------ #

    async def async_poll(self) -> None:
        """If the inverter requires explicit polling, implement here."""
        # For now, the device is notification-driven via JSON commands from elsewhere.
        pass

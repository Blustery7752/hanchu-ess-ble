from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Optional

from bleak import BleakClient, BleakError
from bleak.backends.device import BLEDevice

from homeassistant.core import HomeAssistant, CALLBACK_TYPE
from homeassistant.components.bluetooth import async_ble_device_from_address

from .const import (
    BLE_SERVICE_UUID,
    BLE_SERVICE_UUID_FALLBACK,
    BLE_NOTIFY_CHAR_UUID,
    BLE_WRITE_CHAR_UUID,
)
from .protocol import HanchuProtocol

_LOGGER = logging.getLogger(__name__)

NotificationCallback = Callable[[dict[str, Any]], None]


class HanchuBleClient:
    """BLE client for Hanchu ESS inverter."""

    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        name: str,
        notification_callback: NotificationCallback,
    ) -> None:
        self._hass = hass
        self._address = address
        self._name = name
        self._notification_callback = notification_callback

        self._client: Optional[BleakClient] = None
        self._protocol = HanchuProtocol()
        self._notify_char: Optional[str] = None
        self._write_char: Optional[str] = None

        self._disconnect_callbacks: list[CALLBACK_TYPE] = []
        self._lock = asyncio.Lock()

    @property
    def address(self) -> str:
        return self._address

    @property
    def name(self) -> str:
        return self._name

    def register_disconnect_callback(self, callback: CALLBACK_TYPE) -> None:
        self._disconnect_callbacks.append(callback)

    async def _resolve_ble_device(self) -> BLEDevice:
        """Resolve BLEDevice via HA Bluetooth (supports ESPHome proxies)."""
        ble_device = async_ble_device_from_address(
            self._hass,
            self._address,
            connectable=True,
        )
        if not ble_device:
            raise BleakError(
                f"BLE device {self._address} not found via Home Assistant Bluetooth stack"
            )
        return ble_device

    async def connect(self) -> None:
        """Connect to the inverter via HA Bluetooth backend."""
        async with self._lock:
            if self._client and self._client.is_connected:
                return

            ble_device = await self._hass.async_add_executor_job(
                asyncio.run, self._resolve_ble_device()
            )

            _LOGGER.debug("Connecting to Hanchu inverter at %s (%s)", self._address, self._name)

            self._client = BleakClient(ble_device)

            try:
                await self._client.connect()
            except BleakError as err:
                _LOGGER.error("Failed to connect to %s: %s", self._address, err)
                self._client = None
                raise

            self._client.set_disconnected_callback(self._handle_disconnect)

            await self._discover_characteristics()
            await self._start_notifications()
            await self._send_handshake()

    async def disconnect(self) -> None:
        """Disconnect from the inverter."""
        async with self._lock:
            if self._client and self._client.is_connected:
                _LOGGER.debug("Disconnecting from Hanchu inverter at %s", self._address)
                try:
                    await self._client.disconnect()
                except BleakError as err:
                    _LOGGER.warning("Error during disconnect from %s: %s", self._address, err)
            self._client = None

    def _handle_disconnect(self, _client: BleakClient) -> None:
        _LOGGER.warning("Hanchu inverter at %s disconnected", self._address)
        for cb in list(self._disconnect_callbacks):
            cb()

    async def _discover_characteristics(self) -> None:
        """Discover service and characteristic UUIDs."""
        assert self._client is not None

        services = await self._client.get_services()

        service = services.get_service(BLE_SERVICE_UUID) or services.get_service(
            BLE_SERVICE_UUID_FALLBACK
        )
        if not service:
            raise BleakError("Hanchu BLE service not found on device")

        notify_char = service.get_characteristic(BLE_NOTIFY_CHAR_UUID)
        write_char = service.get_characteristic(BLE_WRITE_CHAR_UUID)

        if not notify_char or not write_char:
            raise BleakError("Notify or write characteristic not found on Hanchu service")

        self._notify_char = notify_char.uuid
        self._write_char = write_char.uuid

        _LOGGER.debug(
            "Using notify char %s and write char %s for %s",
            self._notify_char,
            self._write_char,
            self._address,
        )

    async def _start_notifications(self) -> None:
        """Subscribe to notifications from the inverter."""
        assert self._client is not None
        assert self._notify_char is not None

        await self._client.start_notify(self._notify_char, self._notification_handler)

    async def _send_handshake(self) -> None:
        """Perform dynamic AES key handshake."""
        assert self._client is not None
        assert self._write_char is not None

        random_fix = self._protocol.build_random_fix()
        _LOGGER.debug("Sending randomFix handshake to %s", self._address)
        await self._client.write_gatt_char(self._write_char, random_fix, response=True)

    def _notification_handler(self, _handle: int, data: bytearray) -> None:
        """Handle raw BLE notifications."""
        try:
            telemetry = self._protocol.parse_notification(bytes(data))
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Failed to parse notification from %s: %s", self._address, err)
            return

        if telemetry:
            self._notification_callback(telemetry)

    async def _write_command(self, payload: bytes) -> None:
        """Write an encrypted command to the inverter."""
        assert self._client is not None
        assert self._write_char is not None

        encrypted = self._protocol.encrypt_command(payload)
        await self._client.write_gatt_char(self._write_char, encrypted, response=True)

    # ---------------------------------------------------------------------
    # Public high‑level API used by entities
    # ---------------------------------------------------------------------

    async def async_set_work_mode(self, mode: str) -> None:
        payload = self._protocol.build_set_work_mode(mode)
        await self._write_command(payload)

    async def async_set_charge_power_limit(self, watts: int) -> None:
        payload = self._protocol.build_set_charge_power_limit(watts)
        await self._write_command(payload)

    async def async_set_discharge_power_limit(self, watts: int) -> None:
        payload = self._protocol.build_set_discharge_power_limit(watts)
        await self._write_command(payload)

    async def async_set_max_soc(self, soc: int) -> None:
        payload = self._protocol.build_set_max_soc(soc)
        await self._write_command(payload)

    async def async_set_charge_to_soc(self, soc: int) -> None:
        payload = self._protocol.build_set_charge_to_soc(soc)
        await self._write_command(payload)

    async def async_set_discharge_to_soc(self, soc: int) -> None:
        payload = self._protocol.build_set_discharge_to_soc(soc)
        await self._write_command(payload)

    async def async_set_min_soc(self, soc: int) -> None:
        payload = self._protocol.build_set_min_soc(soc)
        await self._write_command(payload)

    async def async_set_battery_preheat_auto(self, flag: int) -> None:
        payload = self._protocol.build_set_battery_preheat_auto(flag)
        await self._write_command(payload)

    async def async_set_battery_preheat_manual(self, flag: int) -> None:
        payload = self._protocol.build_set_battery_preheat_manual(flag)
        await self._write_command(payload)

    async def async_set_meter_type(self, meter_type: int) -> None:
        payload = self._protocol.build_set_meter_type(meter_type)
        await self._write_command(payload)

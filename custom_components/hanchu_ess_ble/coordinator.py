from __future__ import annotations

import logging
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, MANUFACTURER, MODEL

_LOGGER = logging.getLogger(__name__)


class HanchuBleCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Coordinator that stores the latest telemetry pushed from BLE."""

    def __init__(self, hass: HomeAssistant, ble_client) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Hanchu BLE Coordinator",
            update_interval=None,  # push-based, no polling
        )

        self.ble_client = ble_client
        self.address = ble_client.address
        self.name = ble_client.name

        # Device registry entry
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, self.address)},
            connections={("bluetooth", self.address)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=self.name,
        )

    def handle_notification(self, telemetry: Dict[str, Any]) -> None:
        """Called by BLE client when new telemetry arrives."""
        if not telemetry:
            return

        _LOGGER.debug("Coordinator received telemetry: %s", telemetry)

        # Pass new telemetry to HA and update entities
        self.async_set_updated_data(telemetry)

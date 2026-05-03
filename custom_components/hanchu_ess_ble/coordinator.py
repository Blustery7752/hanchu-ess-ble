from __future__ import annotations

import logging
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

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

    def handle_notification(self, telemetry: Dict[str, Any]) -> None:
        """Called by BLE client when new telemetry arrives."""
        if not telemetry:
            return

        _LOGGER.debug("Coordinator received telemetry: %s", telemetry)

        # Pass new telemetry to HA and update entities
        self.async_set_updated_data(telemetry)
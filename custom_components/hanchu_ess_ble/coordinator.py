from __future__ import annotations

import logging
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class HanchuCoordinator(DataUpdateCoordinator):
    """Coordinator that stores the latest telemetry pushed from BLE."""

    def __init__(self, hass: HomeAssistant, ble_client):
        super().__init__(
            hass,
            _LOGGER,
            name="Hanchu BLE Coordinator",
            update_interval=None,  # push-based, no polling
        )

        self.ble_client = ble_client

        # IMPORTANT: internal state must NOT be called "data"
        self._state: Dict[str, Any] = {}

    @property
    def data(self) -> Dict[str, Any]:
        """Return latest telemetry."""
        return self._state

    def handle_notification(self, telemetry: Dict[str, Any]):
        """Called by BLE client when new telemetry arrives."""
        if not telemetry:
            return

        _LOGGER.debug("Coordinator received telemetry: %s", telemetry)

        # Merge new telemetry into existing state
        self._state.update(telemetry)

        # Notify HA entities
        self.async_set_updated_data(self._state)

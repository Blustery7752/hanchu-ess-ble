from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, MANUFACTURER, MODEL


class HanchuCoordinatorEntity(CoordinatorEntity):
    """Base class for all Hanchu inverter entities."""

    def __init__(self, coordinator):
        super().__init__(coordinator)

        # Device registry entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            connections={("bluetooth", coordinator.address)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=coordinator.data.configured_name,
        )

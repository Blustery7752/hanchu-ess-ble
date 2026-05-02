from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .ble_client import HanchuBleClient
from .coordinator import HanchuCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Hanchu BLE integration."""
    address = entry.data["address"]

    ble_client = HanchuBleClient(hass, entry, address)

    # Coordinator: stores latest telemetry pushed from BLE notifications
    coordinator = HanchuCoordinator(hass, ble_client)

    # Register callback so BLE client pushes updates into coordinator
    ble_client.set_notification_callback(coordinator.handle_notification)

    # Connect BLE immediately
    await ble_client.connect()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "ble_client": ble_client,
        "coordinator": coordinator,
    }

    # Forward platforms
    await hass.config_entries.async_forward_entry_setups(
        entry, ["sensor", "number", "select"]
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload Hanchu BLE integration."""
    data = hass.data[DOMAIN].pop(entry.entry_id)
    ble_client: HanchuBleClient = data["ble_client"]

    await ble_client.disconnect()

    return await hass.config_entries.async_unload_platforms(
        entry, ["sensor", "number", "select"]
    )

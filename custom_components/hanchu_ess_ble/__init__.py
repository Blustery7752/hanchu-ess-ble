from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .ble_client import HanchuBleClient
from .coordinator import HanchuBleCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Hanchu ESS BLE integration."""
    address = entry.data["address"]

    # Create BLE client
    ble_client = HanchuBleClient(hass, entry, address)

    # Create coordinator (push-based)
    coordinator = HanchuBleCoordinator(hass, ble_client)

    # BLE notifications feed into coordinator
    ble_client.set_notification_callback(coordinator.handle_notification)

    # Connect BLE immediately
    await ble_client.connect()

    # Store objects
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
    """Unload Hanchu ESS BLE integration."""
    data = hass.data[DOMAIN].pop(entry.entry_id)
    ble_client: HanchuBleClient = data["ble_client"]

    await ble_client.disconnect()

    return await hass.config_entries.async_unload_platforms(
        entry, ["sensor", "number", "select"]
    )
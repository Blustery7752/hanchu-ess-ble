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

    # 1. Create BLE client first (constructor requires callback)
    #    Use a temporary no-op callback; we replace it after coordinator exists.
    ble_client = HanchuBleClient(
        hass,
        entry,
        address,
        lambda *_: None,   # temporary placeholder
    )

    # 2. Create coordinator WITH the BLE client
    coordinator = HanchuBleCoordinator(hass, ble_client)

    # 3. Now that coordinator exists, set the real callback
    ble_client.set_notification_callback(coordinator.handle_notification)

    # 4. Connect BLE
    await ble_client.connect()

    # 5. Store objects
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "ble_client": ble_client,
        "coordinator": coordinator,
    }

    # 6. Forward platforms
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

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from homeassistant.components.number import (
    NumberEntity,
    NumberDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Number description model
# ---------------------------------------------------------------------------

@dataclass
class HanchuNumberDescription:
    key: str                     # friendly key from protocol
    name: str
    unit: Optional[str]
    min_value: float
    max_value: float
    step: float
    write_fn: Callable[[Any, float], Any]   # (ble_client, value) → awaitable


# ---------------------------------------------------------------------------
# Writable numeric parameters
#
# These keys MUST match protocol.FRIENDLY_MAP output.
# ---------------------------------------------------------------------------

NUMBER_MAP: Dict[str, HanchuNumberDescription] = {
    # Charge power limit (L017)
    "charge_power_limit": HanchuNumberDescription(
        key="charge_power_limit",
        name="Charge Power Limit",
        unit="W",
        min_value=0,
        max_value=10000,
        step=50,
        write_fn=lambda client, v: client.async_set_charge_power_limit(int(v)),
    ),

    # Discharge power limit (L018)
    "discharge_power_limit": HanchuNumberDescription(
        key="discharge_power_limit",
        name="Discharge Power Limit",
        unit="W",
        min_value=0,
        max_value=10000,
        step=50,
        write_fn=lambda client, v: client.async_set_discharge_power_limit(int(v)),
    ),

    # Max SOC limit (L074)
    "max_soc_limit": HanchuNumberDescription(
        key="max_soc_limit",
        name="Max SOC Limit",
        unit="%",
        min_value=10,
        max_value=100,
        step=1,
        write_fn=lambda client, v: client.async_set_max_soc(int(v)),
    ),

    # Charge-to SOC (P647)
    "charge_to_soc": HanchuNumberDescription(
        key="charge_to_soc",
        name="Charge To SOC",
        unit="%",
        min_value=10,
        max_value=100,
        step=1,
        write_fn=lambda client, v: client.async_set_charge_to_soc(int(v)),
    ),

    # Discharge-to SOC (P648)
    "discharge_to_soc": HanchuNumberDescription(
        key="discharge_to_soc",
        name="Discharge To SOC",
        unit="%",
        min_value=0,
        max_value=100,
        step=1,
        write_fn=lambda client, v: client.async_set_discharge_to_soc(int(v)),
    ),

    # Minimum SOC cutoff (P772)
    "min_soc_cutoff": HanchuNumberDescription(
        key="min_soc_cutoff",
        name="Minimum SOC Cutoff",
        unit="%",
        min_value=0,
        max_value=50,
        step=1,
        write_fn=lambda client, v: client.async_set_min_soc(int(v)),
    ),
}


# ---------------------------------------------------------------------------
# Entity setup
# ---------------------------------------------------------------------------

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hanchu BLE number entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    ble_client = data["ble_client"]

    entities = [
        HanchuNumber(coordinator, entry, ble_client, desc)
        for desc in NUMBER_MAP.values()
    ]

    async_add_entities(entities)


# ---------------------------------------------------------------------------
# Number entity
# ---------------------------------------------------------------------------

class HanchuNumber(CoordinatorEntity, NumberEntity):
    """Representation of a writable Hanchu inverter setting."""

    def __init__(self, coordinator, entry, ble_client, description: HanchuNumberDescription):
        super().__init__(coordinator)
        self.entity_description = description
        self._ble_client = ble_client

        self._attr_name = f"Hanchu {description.name}"
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_native_unit_of_measurement = description.unit
        self._attr_native_min_value = description.min_value
        self._attr_native_max_value = description.max_value
        self._attr_native_step = description.step

        self
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from homeassistant.components.number import (
    NumberEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import HanchuCoordinatorEntity
from .coordinator import HanchuBleCoordinator

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Number description model
# ---------------------------------------------------------------------------

@dataclass
class HanchuNumberDescription:
    key: str
    name: str
    unit: Optional[str]
    min_value: float
    max_value: float
    step: float
    write_fn: Callable[[Any, float], Any]  # (ble_client, value) → awaitable


# ---------------------------------------------------------------------------
# Writable numeric parameters
# ---------------------------------------------------------------------------

NUMBER_MAP: Dict[str, HanchuNumberDescription] = {
    "charge_power_limit": HanchuNumberDescription(
        key="charge_power_limit",
        name="Charge Power Limit",
        unit="W",
        min_value=0,
        max_value=10000,
        step=50,
        write_fn=lambda client, v: client.async_set_charge_power_limit(int(v)),
    ),
    "discharge_power_limit": HanchuNumberDescription(
        key="discharge_power_limit",
        name="Discharge Power Limit",
        unit="W",
        min_value=0,
        max_value=10000,
        step=50,
        write_fn=lambda client, v: client.async_set_discharge_power_limit(int(v)),
    ),
    "max_soc_limit": HanchuNumberDescription(
        key="max_soc_limit",
        name="Max SOC Limit",
        unit="%",
        min_value=10,
        max_value=100,
        step=1,
        write_fn=lambda client, v: client.async_set_max_soc(int(v)),
    ),
    "charge_to_soc": HanchuNumberDescription(
        key="charge_to_soc",
        name="Charge To SOC",
        unit="%",
        min_value=10,
        max_value=100,
        step=1,
        write_fn=lambda client, v: client.async_set_charge_to_soc(int(v)),
    ),
    "discharge_to_soc": HanchuNumberDescription(
        key="discharge_to_soc",
        name="Discharge To SOC",
        unit="%",
        min_value=0,
        max_value=100,
        step=1,
        write_fn=lambda client, v: client.async_set_discharge_to_soc(int(v)),
    ),
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
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: HanchuBleCoordinator = data["coordinator"]
    ble_client = data["ble_client"]

    entities = [
        HanchuNumber(coordinator, entry, ble_client, desc)
        for desc in NUMBER_MAP.values()
    ]

    async_add_entities(entities)


# ---------------------------------------------------------------------------
# Number entity
# ---------------------------------------------------------------------------

class HanchuNumber(HanchuCoordinatorEntity, NumberEntity):
    """Representation of a writable Hanchu inverter setting."""

    def __init__(
        self,
        coordinator: HanchuBleCoordinator,
        entry: ConfigEntry,
        ble_client,
        description: HanchuNumberDescription,
    ):
        super().__init__(coordinator)

        self.entity_description = description
        self._ble_client = ble_client

        self._attr_name = description.name
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

        self._attr_native_unit_of_measurement = description.unit
        self._attr_native_min_value = description.min_value
        self._attr_native_max_value = description.max_value
        self._attr_native_step = description.step

    @property
    def native_value(self) -> float | None:
        """Return current value from telemetry."""
        return self.coordinator.data.get(self.entity_description.key)

    async def async_set_native_value(self, value: float) -> None:
        """Write new value to inverter."""
        await self.entity_description.write_fn(self._ble_client, value)

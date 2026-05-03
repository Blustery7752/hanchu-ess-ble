from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, WORK_MODE_MAP_INV
from .entity import HanchuCoordinatorEntity
from .coordinator import HanchuBleCoordinator

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Select description model
# ---------------------------------------------------------------------------

@dataclass
class HanchuSelectDescription:
    key: str
    name: str
    options: List[str]
    write_fn: Callable[[Any, str], Any]  # (ble_client, option) → awaitable


# ---------------------------------------------------------------------------
# Select entities
# ---------------------------------------------------------------------------

SELECT_MAP: Dict[str, HanchuSelectDescription] = {
    "work_mode": HanchuSelectDescription(
        key="work_mode",
        name="Work Mode",
        options=["self_use", "backup", "time_of_use", "off_grid"],
        write_fn=lambda client, opt: client.async_set_work_mode(opt),
    ),
    "battery_preheat_auto": HanchuSelectDescription(
        key="battery_preheat_auto",
        name="Battery Preheat (Auto)",
        options=["off", "on"],
        write_fn=lambda client, opt: client.async_set_battery_preheat_auto(
            1 if opt == "on" else 0
        ),
    ),
    "battery_preheat_manual": HanchuSelectDescription(
        key="battery_preheat_manual",
        name="Battery Preheat (Manual)",
        options=["off", "on"],
        write_fn=lambda client, opt: client.async_set_battery_preheat_manual(
            1 if opt == "on" else 0
        ),
    ),
    "meter_type": HanchuSelectDescription(
        key="meter_type",
        name="Meter Type",
        options=["none", "ct_meter"],
        write_fn=lambda client, opt: client.async_set_meter_type(
            3 if opt == "ct_meter" else 0
        ),
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
        HanchuSelect(coordinator, entry, ble_client, desc)
        for desc in SELECT_MAP.values()
    ]

    async_add_entities(entities)


# ---------------------------------------------------------------------------
# Select entity
# ---------------------------------------------------------------------------

class HanchuSelect(HanchuCoordinatorEntity, SelectEntity):
    """Representation of a Hanchu inverter select entity."""

    def __init__(
        self,
        coordinator: HanchuBleCoordinator,
        entry: ConfigEntry,
        ble_client,
        description: HanchuSelectDescription,
    ):
        super().__init__(coordinator)

        self.entity_description = description
        self._ble_client = ble_client

        self._attr_name = description.name
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_options = description.options

    @property
    def current_option(self) -> Optional[str]:
        """Return the current option from coordinator data."""
        data = self.coordinator.data or {}
        val = data.get(self.entity_description.key)

        if self.entity_description.key == "work_mode":
            return WORK_MODE_MAP_INV.get(val)

        if isinstance(val, int):
            return "on" if val == 1 else "off"

        return val

    async def async_select_option(self, option: str) -> None:
        """Write the new option to the inverter."""
        desc = self.entity_description
        _LOGGER.debug("Setting %s to %s", desc.key, option)

        await desc.write_fn(self._ble_client, option)
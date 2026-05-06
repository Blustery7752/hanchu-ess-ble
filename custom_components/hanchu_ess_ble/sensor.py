from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import HanchuCoordinatorEntity
from .coordinator import HanchuBleCoordinator

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sensor description model
# ---------------------------------------------------------------------------

@dataclass
class HanchuSensorDescription:
    key: str
    name: str
    unit: Optional[str] = None
    device_class: Optional[str] = None
    state_class: Optional[str] = None
    value_fn: Optional[Callable[[Dict[str, Any]], Any]] = None


# ---------------------------------------------------------------------------
# Sensors (must match protocol.FRIENDLY_MAP)
# ---------------------------------------------------------------------------

SENSOR_MAP: Dict[str, HanchuSensorDescription] = {
    # PV
    "pv1_voltage": HanchuSensorDescription(
        key="pv1_voltage",
        name="PV1 Voltage",
        unit="V",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "pv1_current": HanchuSensorDescription(
        key="pv1_current",
        name="PV1 Current",
        unit="A",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "pv2_voltage": HanchuSensorDescription(
        key="pv2_voltage",
        name="PV2 Voltage",
        unit="V",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "pv2_current": HanchuSensorDescription(
        key="pv2_current",
        name="PV2 Current",
        unit="A",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "pv_power_total": HanchuSensorDescription(
        key="pv_power_total",
        name="PV Power Total",
        unit="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),

    # Grid
    "grid_voltage": HanchuSensorDescription(
        key="grid_voltage",
        name="Grid Voltage",
        unit="V",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "grid_current": HanchuSensorDescription(
        key="grid_current",
        name="Grid Current",
        unit="A",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "grid_frequency": HanchuSensorDescription(
        key="grid_frequency",
        name="Grid Frequency",
        unit="Hz",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "grid_power": HanchuSensorDescription(
        key="grid_power",
        name="Grid Active Power",
        unit="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),

    # Load
    "load_power": HanchuSensorDescription(
        key="load_power",
        name="Load Power",
        unit="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),

    # Battery
    "battery_soc": HanchuSensorDescription(
        key="battery_soc",
        name="Battery State of Charge",
        unit="%",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: round(d.get("battery_soc", 0) * 100, 1)
        if isinstance(d.get("battery_soc"), (int, float))
        else d.get("battery_soc"),
    ),
    "battery_voltage": HanchuSensorDescription(
        key="battery_voltage",
        name="Battery Voltage",
        unit="V",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "battery_current": HanchuSensorDescription(
        key="battery_current",
        name="Battery Current",
        unit="A",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "battery_temperature": HanchuSensorDescription(
        key="battery_temperature",
        name="Battery Temperature",
        unit="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),

    # Work mode
    "work_mode": HanchuSensorDescription(
        key="work_mode",
        name="Work Mode",
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

    entities = [
        HanchuSensor(coordinator, entry, desc)
        for desc in SENSOR_MAP.values()
    ]

    async_add_entities(entities)


# ---------------------------------------------------------------------------
# Sensor entity
# ---------------------------------------------------------------------------

class HanchuSensor(HanchuCoordinatorEntity, SensorEntity):
    """Representation of a Hanchu inverter sensor."""

    def __init__(self, coordinator, entry, description: HanchuSensorDescription):
        super().__init__(coordinator)

        self.entity_description = description
        self._attr_name = description.name
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        desc = self.entity_description

        if desc.value_fn:
            return desc.value_fn(data)

        value = data.get(desc.key)
        return value if isinstance(value, (int, float)) else None


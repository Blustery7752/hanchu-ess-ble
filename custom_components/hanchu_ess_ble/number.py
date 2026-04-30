"""Number entities for writable Hanchu inverter settings."""

from __future__ import annotations

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HanchuBleCoordinator
from .entity import HanchuCoordinatorEntity


WRITABLE_NUMBERS: tuple[NumberEntityDescription, ...] = (
    NumberEntityDescription(
        key="L017",
        name="Charging Power Maximum",
        native_min_value=0,
        native_max_value=100000,
        native_step=1,
        native_unit_of_measurement=UnitOfPower.WATT,
        mode=NumberMode.BOX,
    ),
    NumberEntityDescription(
        key="L018",
        name="Discharging Power Maximum",
        native_min_value=0,
        native_max_value=100000,
        native_step=1,
        native_unit_of_measurement=UnitOfPower.WATT,
        mode=NumberMode.BOX,
    ),
    NumberEntityDescription(
        key="L074",
        name="Grid-to-battery maximum SoC",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.BOX,
    ),
    NumberEntityDescription(
        key="P647",
        name="Maximum charge SoC",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.BOX,
    ),
    NumberEntityDescription(
        key="P648",
        name="On-grid Battery discharge minimum",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.BOX,
    ),
    NumberEntityDescription(
        key="P772",
        name="Off-grid Battery discharge minimum",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.BOX,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hanchu writable number entities from a config entry."""
    coordinator: HanchuBleCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        HanchuWritableNumber(coordinator, description)
        for description in WRITABLE_NUMBERS
    )


class HanchuWritableNumber(HanchuCoordinatorEntity, NumberEntity):
    """Writable numeric inverter setting."""

    entity_description: NumberEntityDescription

    def __init__(
        self,
        coordinator: HanchuBleCoordinator,
        description: NumberEntityDescription,
    ) -> None:
        """Initialise the number entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.address}_{description.key.lower()}_setting"

    @property
    def native_value(self) -> float | None:
        """Return the current setting value."""
        value = (self.coordinator.data.values or {}).get(self.entity_description.key)
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Write the setting value to the inverter."""
        await self.coordinator.async_write_value(self.entity_description.key, int(value))

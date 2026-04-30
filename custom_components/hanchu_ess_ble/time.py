"""Time entities for writable Hanchu inverter schedules."""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HanchuBleCoordinator
from .entity import HanchuCoordinatorEntity


SECONDS_PER_DAY = 24 * 60 * 60

WRITABLE_TIMES: tuple[TimeEntityDescription, ...] = (
    TimeEntityDescription(key="L005", name="Charge time 1 start"),
    TimeEntityDescription(key="L006", name="Charge time 1 end"),
    TimeEntityDescription(key="L007", name="Charge time 2 start"),
    TimeEntityDescription(key="L008", name="Charge time 2 end"),
    TimeEntityDescription(key="L009", name="Charge time 3 start"),
    TimeEntityDescription(key="L010", name="Charge time 3 end"),
    TimeEntityDescription(key="L011", name="Discharge time 1 start"),
    TimeEntityDescription(key="L012", name="Discharge time 1 end"),
    TimeEntityDescription(key="L013", name="Discharge time 2 start"),
    TimeEntityDescription(key="L014", name="Discharge time 2 end"),
    TimeEntityDescription(key="L015", name="Discharge time 3 start"),
    TimeEntityDescription(key="L016", name="Discharge time 3 end"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hanchu writable schedule time entities from a config entry."""
    coordinator: HanchuBleCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        HanchuWritableTime(coordinator, description) for description in WRITABLE_TIMES
    )


class HanchuWritableTime(HanchuCoordinatorEntity, TimeEntity):
    """Writable inverter schedule time."""

    _attr_entity_registry_enabled_default = False

    entity_description: TimeEntityDescription

    def __init__(
        self,
        coordinator: HanchuBleCoordinator,
        description: TimeEntityDescription,
    ) -> None:
        """Initialise the time entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.address}_{description.key.lower()}_setting"

    @property
    def native_value(self) -> time | None:
        """Return the schedule value as a local time."""
        value = (self.coordinator.data.values or {}).get(self.entity_description.key)
        if value is None:
            return None

        try:
            seconds = int(value)
        except (TypeError, ValueError):
            return None

        if not 0 <= seconds < SECONDS_PER_DAY:
            return None

        hours, remainder = divmod(seconds, 60 * 60)
        minutes, seconds = divmod(remainder, 60)
        return time(hour=hours, minute=minutes, second=seconds)

    async def async_set_value(self, value: time) -> None:
        """Write the schedule value to the inverter as seconds past midnight."""
        seconds = value.hour * 60 * 60 + value.minute * 60 + value.second
        await self.coordinator.async_write_value(self.entity_description.key, seconds)

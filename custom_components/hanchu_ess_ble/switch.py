"""Switch entities for Hanchu inverter schedule windows."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HanchuBleCoordinator
from .entity import HanchuCoordinatorEntity


@dataclass(frozen=True, kw_only=True)
class HanchuScheduleSwitchDescription(SwitchEntityDescription):
    """Description for a charge/discharge schedule enable switch."""

    start_key: str
    end_key: str


SCHEDULE_SWITCHES: tuple[HanchuScheduleSwitchDescription, ...] = (
    HanchuScheduleSwitchDescription(
        key="charge_time_1_enabled",
        name="Charge time 1 enabled",
        start_key="L005",
        end_key="L006",
    ),
    HanchuScheduleSwitchDescription(
        key="charge_time_2_enabled",
        name="Charge time 2 enabled",
        start_key="L007",
        end_key="L008",
    ),
    HanchuScheduleSwitchDescription(
        key="charge_time_3_enabled",
        name="Charge time 3 enabled",
        start_key="L009",
        end_key="L010",
    ),
    HanchuScheduleSwitchDescription(
        key="discharge_time_1_enabled",
        name="Discharge time 1 enabled",
        start_key="L011",
        end_key="L012",
    ),
    HanchuScheduleSwitchDescription(
        key="discharge_time_2_enabled",
        name="Discharge time 2 enabled",
        start_key="L013",
        end_key="L014",
    ),
    HanchuScheduleSwitchDescription(
        key="discharge_time_3_enabled",
        name="Discharge time 3 enabled",
        start_key="L015",
        end_key="L016",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hanchu schedule switches from a config entry."""
    coordinator: HanchuBleCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        HanchuScheduleSwitch(coordinator, description)
        for description in SCHEDULE_SWITCHES
    )


def _int_or_zero(value: object) -> int:
    """Return an integer value, or zero when the register is missing/invalid."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


class HanchuScheduleSwitch(HanchuCoordinatorEntity, SwitchEntity):
    """Enable switch for a charge/discharge schedule window."""

    entity_description: HanchuScheduleSwitchDescription

    def __init__(
        self,
        coordinator: HanchuBleCoordinator,
        description: HanchuScheduleSwitchDescription,
    ) -> None:
        """Initialise the switch entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.address}_{description.key}"
        self._last_enabled_values: dict[str, int] | None = None

    @property
    def is_on(self) -> bool:
        """Return true when either schedule register contains a non-zero value."""
        values = self.coordinator.data.values or {}
        return (
            _int_or_zero(values.get(self.entity_description.start_key)) != 0
            or _int_or_zero(values.get(self.entity_description.end_key)) != 0
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Disable the schedule window by zeroing both time registers."""
        del kwargs
        values = self.coordinator.data.values or {}
        start_value = _int_or_zero(values.get(self.entity_description.start_key))
        end_value = _int_or_zero(values.get(self.entity_description.end_key))
        if start_value != 0 or end_value != 0:
            self._last_enabled_values = {
                self.entity_description.start_key: start_value,
                self.entity_description.end_key: end_value,
            }

        await self.coordinator.async_write_values(
            {
                self.entity_description.start_key: 0,
                self.entity_description.end_key: 0,
            }
        )

    async def async_turn_on(self, **kwargs) -> None:
        """Restore the previous schedule window, or create a minimal enabled one."""
        del kwargs
        values = self.coordinator.data.values or {}
        start_value = _int_or_zero(values.get(self.entity_description.start_key))
        end_value = _int_or_zero(values.get(self.entity_description.end_key))
        if start_value != 0 or end_value != 0:
            return

        await self.coordinator.async_write_values(
            self._last_enabled_values
            or {
                self.entity_description.start_key: 0,
                self.entity_description.end_key: 60,
            }
        )

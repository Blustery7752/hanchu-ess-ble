from __future__ import annotations

import re
import voluptuous as vol
from typing import Any, Dict

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN


MAC_REGEX = re.compile(r"^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$")


def _validate_mac(address: str) -> bool:
    """Return True if the string looks like a BLE MAC address."""
    return bool(MAC_REGEX.match(address))


class HanchuConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hanchu ESS BLE."""

    VERSION = 1

    async def async_step_user(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        """Initial step: ask for BLE MAC address."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            address = user_input.get("address", "").strip()

            # Validate MAC format
            if not _validate_mac(address):
                errors["address"] = "invalid_mac"
            else:
                # Prevent duplicates
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Hanchu ESS ({address})",
                    data={"address": address},
                )

        schema = vol.Schema(
            {
                vol.Required("address"): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

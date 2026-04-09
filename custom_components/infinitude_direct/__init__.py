"""Infinitude Direct — HA climate integration for Carrier/Bryant Infinity thermostats."""

import json
import logging
from pathlib import Path

import voluptuous as vol

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from .const import CONF_HOST, DOMAIN
from .coordinator import InfinitudeDataCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CLIMATE, Platform.SELECT, Platform.SENSOR]

CARD_URL = "/infinitude_direct/infinitude-hvac-card.js"
CARD_PATH = Path(__file__).parent / "www" / "infinitude-hvac-card.js"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = InfinitudeDataCoordinator(hass, entry.data[CONF_HOST])
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    _register_services(hass)

    # Serve the custom card JS
    await _register_card(hass)

    return True


async def _register_card(hass: HomeAssistant) -> None:
    """Register static path for the custom Lovelace card."""
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(CARD_PATH), False)]
        )
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Static path %s already registered", CARD_URL)


def _register_services(hass: HomeAssistant) -> None:
    """Register custom services for schedule/profile management."""

    async def handle_save_schedule(call: ServiceCall) -> None:
        zone_id = call.data["zone_id"]
        schedule_data = call.data["schedule"]
        if isinstance(schedule_data, str):
            schedule_data = json.loads(schedule_data)
        for entry_id, coordinator in hass.data[DOMAIN].items():
            if isinstance(coordinator, InfinitudeDataCoordinator):
                await coordinator.async_save_schedule(zone_id, schedule_data)
                await coordinator.async_request_refresh()
                return

    async def handle_set_profile(call: ServiceCall) -> None:
        zone_id = call.data["zone_id"]
        activity = call.data["activity"]
        htsp = int(call.data["htsp"])
        clsp = int(call.data["clsp"])
        fan = call.data.get("fan")
        for entry_id, coordinator in hass.data[DOMAIN].items():
            if isinstance(coordinator, InfinitudeDataCoordinator):
                await coordinator.async_set_activity_temps(
                    zone_id, activity, htsp, clsp
                )
                if fan:
                    await coordinator.async_set_activity_fan(
                        zone_id, activity, fan
                    )
                await coordinator.async_request_refresh()
                return

    hass.services.async_register(
        DOMAIN,
        "save_schedule",
        handle_save_schedule,
        schema=vol.Schema({
            vol.Required("zone_id"): cv.string,
            vol.Required("schedule"): vol.Any(list, cv.string),
        }),
    )

    hass.services.async_register(
        DOMAIN,
        "set_profile",
        handle_set_profile,
        schema=vol.Schema({
            vol.Required("zone_id"): cv.string,
            vol.Required("activity"): cv.string,
            vol.Required("htsp"): vol.Coerce(int),
            vol.Required("clsp"): vol.Coerce(int),
            vol.Optional("fan"): cv.string,
        }),
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

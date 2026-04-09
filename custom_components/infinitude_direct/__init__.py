"""Infinitude Direct — HA climate integration for Carrier/Bryant Infinity thermostats."""

import json
import logging
import shutil
from pathlib import Path

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv

from .const import CONF_HOST, DOMAIN
from .coordinator import InfinitudeDataCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CLIMATE, Platform.SELECT, Platform.SENSOR]

CARD_FILENAME = "infinitude-hvac-card.js"
CARD_DIR = "www/community/infinitude_direct"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Infinitude Direct domain (card installation)."""
    await _install_card(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Also install card here in case async_setup was skipped
    await _install_card(hass)
    coordinator = InfinitudeDataCoordinator(hass, entry.data[CONF_HOST])
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    _register_services(hass)

    return True


async def _install_card(hass: HomeAssistant) -> None:
    """Copy card JS to HA www directory so /local/ can serve it."""
    src = Path(__file__).parent / "www" / CARD_FILENAME
    dst_dir = Path(hass.config.path(CARD_DIR))
    dst = dst_dir / CARD_FILENAME

    _LOGGER.warning(
        "HVAC card install: src=%s exists=%s, dst=%s", src, src.is_file(), dst
    )

    def _copy() -> None:
        dst_dir.mkdir(parents=True, exist_ok=True)
        if src.is_file():
            shutil.copy2(src, dst)
            _LOGGER.warning("Installed HVAC card JS → %s (size=%d)", dst, dst.stat().st_size)
        else:
            _LOGGER.error(
                "HVAC card JS source not found: %s  parent contents: %s",
                src, list(src.parent.parent.iterdir()) if src.parent.parent.is_dir() else "N/A",
            )

    try:
        await hass.async_add_executor_job(_copy)
    except Exception:
        _LOGGER.exception("Failed to install HVAC card JS")


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

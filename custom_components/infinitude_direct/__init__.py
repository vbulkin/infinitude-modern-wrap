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
CARD_URL = "/local/community/infinitude_direct/infinitude-hvac-card.js"
DASHBOARD_URL_PATH = "hvac-panel"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Infinitude Direct domain."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Infinitude Direct from a config entry."""
    coordinator = InfinitudeDataCoordinator(hass, entry.data[CONF_HOST])
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _register_services(hass)

    # Install card, resource, and dashboard (fire-and-forget)
    hass.async_create_task(_setup_frontend(hass))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry (disable — keep dashboard/resources)."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry (full uninstall). Clean up all frontend assets."""
    _LOGGER.info("Removing Infinitude Direct — cleaning up frontend assets")
    await _remove_lovelace_resource(hass)
    await _remove_dashboard(hass)
    await _remove_card_file(hass)


# ── Frontend Setup ───────────────────────────────────────────────────────

async def _setup_frontend(hass: HomeAssistant) -> None:
    """Install card JS, register Lovelace resource, and create dashboard."""
    await _install_card(hass)
    await _ensure_lovelace_resource(hass)
    await _ensure_dashboard(hass)


async def _install_card(hass: HomeAssistant) -> None:
    """Copy card JS to HA www directory so /local/ can serve it."""
    src = Path(__file__).parent / "www" / CARD_FILENAME
    dst_dir = Path(hass.config.path(CARD_DIR))
    dst = dst_dir / CARD_FILENAME

    def _copy() -> None:
        dst_dir.mkdir(parents=True, exist_ok=True)
        if src.is_file():
            shutil.copy2(src, dst)
        else:
            _LOGGER.error("Card JS source not found: %s", src)

    try:
        await hass.async_add_executor_job(_copy)
    except Exception:
        _LOGGER.exception("Failed to install card JS")


async def _ensure_lovelace_resource(hass: HomeAssistant) -> None:
    """Register the card JS as a Lovelace resource if not already present."""
    try:
        lovelace = hass.data.get("lovelace")
        if not lovelace:
            return

        resources = lovelace.resources
        if not hasattr(resources, "store") or resources.store is None:
            return  # YAML mode

        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True

        # Check if already registered
        for item in resources.async_items():
            if CARD_URL in item.get("url", ""):
                return

        await resources.async_create_item({
            "res_type": "module",
            "url": CARD_URL,
        })
        _LOGGER.info("Registered Lovelace resource: %s", CARD_URL)
    except Exception:
        _LOGGER.exception("Failed to register Lovelace resource")


async def _ensure_dashboard(hass: HomeAssistant) -> None:
    """Create the HVAC dashboard if it doesn't already exist."""
    try:
        lovelace = hass.data.get("lovelace")
        if not lovelace or not hasattr(lovelace, "dashboards"):
            return

        # Already exists?
        if DASHBOARD_URL_PATH in lovelace.dashboards:
            return

        dashboards = lovelace.dashboards_collection

        await dashboards.async_create_item({
            "url_path": DASHBOARD_URL_PATH,
            "title": "HVAC",
            "icon": "mdi:hvac",
            "show_in_sidebar": True,
            "require_admin": False,
        })

        # Save dashboard view config
        dashboard_obj = lovelace.dashboards.get(DASHBOARD_URL_PATH)
        if dashboard_obj:
            await dashboard_obj.async_save({
                "views": [{
                    "path": "hvac-main",
                    "title": "HVAC",
                    "type": "panel",
                    "cards": [{"type": "custom:infinitude-hvac-card"}],
                }]
            })
        _LOGGER.info("Created HVAC dashboard")
    except Exception:
        _LOGGER.exception("Failed to create HVAC dashboard")


# ── Frontend Cleanup ─────────────────────────────────────────────────────

async def _remove_lovelace_resource(hass: HomeAssistant) -> None:
    """Remove the card JS Lovelace resource."""
    try:
        lovelace = hass.data.get("lovelace")
        if not lovelace:
            return

        resources = lovelace.resources
        if not hasattr(resources, "store") or resources.store is None:
            return

        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True

        for item in resources.async_items():
            if "infinitude_direct" in item.get("url", ""):
                await resources.async_delete_item(item["id"])
                _LOGGER.info("Removed Lovelace resource: %s", item["url"])
                return
    except Exception:
        _LOGGER.exception("Failed to remove Lovelace resource")


async def _remove_dashboard(hass: HomeAssistant) -> None:
    """Remove the HVAC dashboard."""
    try:
        lovelace = hass.data.get("lovelace")
        if not lovelace or not hasattr(lovelace, "dashboards_collection"):
            return

        dashboards = lovelace.dashboards_collection
        for db in dashboards.async_items():
            if db.get("url_path") == DASHBOARD_URL_PATH:
                await dashboards.async_delete_item(db["id"])
                _LOGGER.info("Removed HVAC dashboard")
                return
    except Exception:
        _LOGGER.exception("Failed to remove HVAC dashboard")


async def _remove_card_file(hass: HomeAssistant) -> None:
    """Remove the copied card JS and its directory."""
    card_dir = Path(hass.config.path(CARD_DIR))

    def _delete() -> None:
        if card_dir.is_dir():
            shutil.rmtree(card_dir)
            _LOGGER.info("Removed card directory: %s", card_dir)

    try:
        await hass.async_add_executor_job(_delete)
    except Exception:
        _LOGGER.exception("Failed to remove card files")


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

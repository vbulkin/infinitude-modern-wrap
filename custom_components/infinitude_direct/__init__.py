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

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.SELECT,
    Platform.SENSOR,
]

CARD_FILENAME = "infinitude-hvac-card.js"
CARD_DIR = "www/community/infinitude_direct"
CARD_URL_BASE = "/local/community/infinitude_direct/infinitude-hvac-card.js"
DASHBOARD_URL_PATH = "hvac-panel"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Infinitude Direct domain."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Infinitude Direct from a config entry."""
    coordinator = InfinitudeDataCoordinator(hass, entry.data[CONF_HOST])
    await coordinator.async_config_entry_first_refresh()
    # Start the SSE consumer AFTER the first refresh so we already
    # have a baseline `data` shape before any events land. The
    # coordinator's async_shutdown cancels the task on unload.
    coordinator.start_sse()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    if not hass.services.has_service(DOMAIN, "save_schedule"):
        _register_services(hass)

    # Reload integration when options (host URL) change
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Install card, resource, and dashboard (fire-and-forget)
    hass.async_create_task(_setup_frontend(hass))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when configuration changes."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry (disable — keep dashboard/resources)."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id, None)
        if coordinator is not None:
            # Explicit shutdown cancels the SSE consumer task. HA's
            # DataUpdateCoordinator doesn't call this automatically;
            # without it, the task survives the reload and we'd
            # accumulate consumers on every options-flow change.
            await coordinator.async_shutdown()
        if not hass.data[DOMAIN]:
            _unregister_services(hass)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry (full uninstall). Clean up all frontend assets."""
    _LOGGER.info("Removing Infinitude Direct — cleaning up frontend assets")
    await _remove_lovelace_resource(hass)
    await _remove_dashboard(hass)
    await _remove_card_file(hass)
    await _remove_dashboard_storage(hass)
    _unregister_services(hass)


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
    except OSError:
        _LOGGER.exception("Failed to install card JS")


async def _ensure_lovelace_resource(hass: HomeAssistant) -> None:
    """Register or update the card JS Lovelace resource with cache-busting version."""
    try:
        lovelace = hass.data.get("lovelace")
        if not lovelace:
            return

        resources = getattr(lovelace, 'resources', None)
        if resources is None or not hasattr(resources, "store") or resources.store is None:
            return  # YAML mode

        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True

        # Read version from manifest for cache-busting (off-loop to keep
        # HA happy — read_text in the event loop trips a blocking-call
        # warning on recent cores).
        manifest = Path(__file__).parent / "manifest.json"
        version = "0"
        if manifest.is_file():
            text = await hass.async_add_executor_job(manifest.read_text)
            version = json.loads(text).get("version", "0")
        card_url = f"{CARD_URL_BASE}?v={version}"

        # Check if already registered
        for item in resources.async_items():
            if CARD_URL_BASE in item.get("url", ""):
                # Update URL if version changed
                item_id = item.get("id")
                if item.get("url") != card_url and item_id:
                    await resources.async_update_item(
                        item_id, {"url": card_url}
                    )
                    _LOGGER.info("Updated Lovelace resource to: %s", card_url)
                return

        await resources.async_create_item({
            "res_type": "module",
            "url": card_url,
        })
        _LOGGER.info("Registered Lovelace resource: %s", card_url)
    except Exception:  # HA Lovelace internals — no stable API to catch narrower types
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
    except Exception:  # HA Lovelace internals — no stable API to catch narrower types
        _LOGGER.exception("Failed to create HVAC dashboard")


# ── Frontend Cleanup ─────────────────────────────────────────────────────

async def _remove_lovelace_resource(hass: HomeAssistant) -> None:
    """Remove the card JS Lovelace resource."""
    try:
        lovelace = hass.data.get("lovelace")
        if not lovelace:
            return

        resources = getattr(lovelace, 'resources', None)
        if resources is None or not hasattr(resources, "store") or resources.store is None:
            return

        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True

        for item in resources.async_items():
            if "infinitude_direct" in item.get("url", ""):
                item_id = item.get("id")
                if item_id:
                    await resources.async_delete_item(item_id)
                    _LOGGER.info("Removed Lovelace resource: %s", item.get("url"))
                return
    except Exception:  # HA Lovelace internals — no stable API to catch narrower types
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
                db_id = db.get("id")
                if db_id:
                    await dashboards.async_delete_item(db_id)
                    _LOGGER.info("Removed HVAC dashboard")
                return
    except Exception:  # HA Lovelace internals — no stable API to catch narrower types
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
    except OSError:
        _LOGGER.exception("Failed to remove card files")


async def _remove_dashboard_storage(hass: HomeAssistant) -> None:
    """Remove the dashboard view config storage file."""
    storage_file = Path(hass.config.path(".storage")) / f"lovelace.{DASHBOARD_URL_PATH}"

    def _delete() -> None:
        if storage_file.is_file():
            storage_file.unlink()
            _LOGGER.info("Removed dashboard storage: %s", storage_file)

    try:
        await hass.async_add_executor_job(_delete)
    except OSError:
        _LOGGER.exception("Failed to remove dashboard storage")


def _register_services(hass: HomeAssistant) -> None:
    """Register custom services for schedule/profile management."""

    def _coordinator() -> InfinitudeDataCoordinator | None:
        """Return the first active coordinator, or None."""
        for coordinator in hass.data[DOMAIN].values():
            if isinstance(coordinator, InfinitudeDataCoordinator):
                return coordinator
        return None

    async def handle_save_schedule(call: ServiceCall) -> None:
        zone_id = call.data["zone_id"]
        schedule_data = call.data["schedule"]
        if isinstance(schedule_data, str):
            try:
                schedule_data = json.loads(schedule_data)
            except json.JSONDecodeError:
                _LOGGER.error("Invalid JSON in schedule data")
                return
        c = _coordinator()
        if not c:
            _LOGGER.warning("save_schedule: no active coordinator found")
            return
        await c.async_save_schedule(zone_id, schedule_data)
        await c.async_request_refresh()

    async def handle_set_profile(call: ServiceCall) -> None:
        zone_id = call.data["zone_id"]
        activity = call.data["activity"]
        htsp = int(call.data["htsp"])
        clsp = int(call.data["clsp"])
        fan = call.data.get("fan")
        c = _coordinator()
        if not c:
            _LOGGER.warning("set_profile: no active coordinator found")
            return
        await c.async_set_activity_temps(zone_id, activity, htsp, clsp)
        if fan:
            await c.async_set_activity_fan(zone_id, activity, fan)
        await c.async_request_refresh()

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

    async def handle_cancel_hold(call: ServiceCall) -> None:
        zone_id = call.data["zone_id"]
        c = _coordinator()
        if not c:
            _LOGGER.warning("cancel_hold: no active coordinator found")
            return
        await c.async_cancel_hold(zone_id)
        await c.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        "cancel_hold",
        handle_cancel_hold,
        schema=vol.Schema({
            vol.Required("zone_id"): cv.string,
        }),
    )

    async def handle_set_hold(call: ServiceCall) -> None:
        zone_id = call.data["zone_id"]
        activity = call.data["activity"]
        until = call.data.get("until")
        c = _coordinator()
        if not c:
            _LOGGER.warning("set_hold: no active coordinator found")
            return
        await c.async_set_hold(zone_id, activity, until)
        await c.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        "set_hold",
        handle_set_hold,
        schema=vol.Schema({
            vol.Required("zone_id"): cv.string,
            vol.Required("activity"): cv.string,
            vol.Optional("until"): cv.string,
        }),
    )

    async def handle_set_whole_house_hold(call: ServiceCall) -> None:
        activity = call.data["activity"]
        until = call.data.get("until")
        c = _coordinator()
        if not c:
            _LOGGER.warning("set_whole_house_hold: no active coordinator found")
            return
        await c.async_set_whole_house_hold(activity, until)
        await c.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        "set_whole_house_hold",
        handle_set_whole_house_hold,
        schema=vol.Schema({
            vol.Required("activity"): cv.string,
            vol.Optional("until"): cv.string,
        }),
    )

    async def handle_cancel_whole_house_hold(call: ServiceCall) -> None:
        c = _coordinator()
        if not c:
            _LOGGER.warning("cancel_whole_house_hold: no active coordinator found")
            return
        await c.async_cancel_whole_house_hold()
        await c.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        "cancel_whole_house_hold",
        handle_cancel_whole_house_hold,
        schema=vol.Schema({}),
    )

    async def handle_set_vacation(call: ServiceCall) -> None:
        c = _coordinator()
        if not c:
            _LOGGER.warning("set_vacation: no active coordinator found")
            return
        kwargs: dict = {}
        if "active" in call.data:
            kwargs["active"] = bool(call.data["active"])
        if "start" in call.data:
            kwargs["start"] = call.data["start"]
        if "end" in call.data:
            kwargs["end"] = call.data["end"]
        if "heat_setpoint" in call.data:
            kwargs["heat_setpoint"] = int(call.data["heat_setpoint"])
        if "cool_setpoint" in call.data:
            kwargs["cool_setpoint"] = int(call.data["cool_setpoint"])
        if "fan" in call.data:
            kwargs["fan"] = call.data["fan"]
        await c.async_set_vacation(**kwargs)
        await c.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        "set_vacation",
        handle_set_vacation,
        schema=vol.Schema({
            vol.Optional("active"): cv.boolean,
            vol.Optional("start"): cv.string,
            vol.Optional("end"): cv.string,
            vol.Optional("heat_setpoint"): vol.Coerce(int),
            vol.Optional("cool_setpoint"): vol.Coerce(int),
            vol.Optional("fan"): cv.string,
        }),
    )

    async def handle_cancel_vacation(call: ServiceCall) -> None:
        c = _coordinator()
        if not c:
            _LOGGER.warning("cancel_vacation: no active coordinator found")
            return
        await c.async_cancel_vacation()
        await c.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        "cancel_vacation",
        handle_cancel_vacation,
        schema=vol.Schema({}),
    )


def _unregister_services(hass: HomeAssistant) -> None:
    """Remove all custom services."""
    for svc in (
        "save_schedule", "set_profile", "cancel_hold",
        "set_hold", "set_whole_house_hold", "cancel_whole_house_hold",
        "set_vacation", "cancel_vacation",
    ):
        if hass.services.has_service(DOMAIN, svc):
            hass.services.async_remove(DOMAIN, svc)

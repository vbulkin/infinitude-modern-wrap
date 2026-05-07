"""Binary sensors for Infinitude Direct.

Two entities:
  * `binary_sensor.infinitude_fault_active` — mirrors the thermostat's
    `<active>on</active>` flag on any event in `/v1/system/events`.
    Useful for automations that should fire when the HVAC reports a
    problem.
  * `binary_sensor.infinitude_vacation` — vacation-mode flag from
    `/v1/system/vacation`, with the configured window + setpoints
    surfaced as attributes for dashboards / templates.
"""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import InfinitudeDataCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: InfinitudeDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        InfinitudeFaultActiveBinarySensor(coordinator),
        InfinitudeVacationBinarySensor(coordinator),
    ])


class InfinitudeFaultActiveBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """ON when any event in the equipment-events list has
    `active=true`. The full event list is exposed as attributes on
    the companion `sensor.infinitude_fault_count`."""

    _attr_has_entity_name = True
    _attr_name = "Fault active"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:alert-circle"

    def __init__(self, coordinator: InfinitudeDataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "infinitude_fault_active"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "system")},
            name="Infinitude System",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def available(self) -> bool:
        return (
            super().available
            and not self.coordinator.data.get("stale", False)
            and self.coordinator.data.get("events") is not None
        )

    @property
    def is_on(self) -> bool:
        events_data = self.coordinator.data.get("events") or {}
        events = events_data.get("events", []) or []
        return any(e.get("active") for e in events)

    @property
    def extra_state_attributes(self) -> dict:
        events_data = self.coordinator.data.get("events") or {}
        events = events_data.get("events", []) or []
        active = [e for e in events if e.get("active")]
        # Most-recent active fault first — useful for templates.
        latest = active[0] if active else None
        return {
            "active_count": len(active),
            "latest_code": (latest or {}).get("code"),
            "latest_description": (latest or {}).get("description"),
            "latest_source": (latest or {}).get("source"),
            "latest_local_time": (latest or {}).get("localTime"),
        }


class InfinitudeVacationBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """ON when the system is currently in vacation mode (`active=true`
    on `/v1/system/vacation`). Attributes carry the configured start,
    end, vacation-mode setpoints, and fan speed so dashboards can show
    the schedule without templating against `climate.*`'s
    `extra_state_attributes`.
    """

    _attr_has_entity_name = True
    _attr_name = "Vacation"
    _attr_icon = "mdi:airplane"

    def __init__(self, coordinator: InfinitudeDataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "infinitude_vacation"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "system")},
            name="Infinitude System",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def available(self) -> bool:
        return (
            super().available
            and not self.coordinator.data.get("stale", False)
            and self.coordinator.data.get("vacation") is not None
        )

    @property
    def is_on(self) -> bool:
        vac = self.coordinator.data.get("vacation") or {}
        return bool(vac.get("active"))

    @property
    def extra_state_attributes(self) -> dict:
        vac = self.coordinator.data.get("vacation") or {}
        attrs: dict = {}
        if vac.get("start"):
            attrs["start"] = vac["start"]
        if vac.get("end"):
            attrs["end"] = vac["end"]
        if vac.get("heatSetpoint") is not None:
            attrs["heat_setpoint"] = int(vac["heatSetpoint"])
        if vac.get("coolSetpoint") is not None:
            attrs["cool_setpoint"] = int(vac["coolSetpoint"])
        if vac.get("fan"):
            attrs["fan"] = vac["fan"]
        return attrs

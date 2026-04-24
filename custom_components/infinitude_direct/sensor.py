"""Sensor platform for Infinitude Direct."""

import json
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import InfinitudeDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: InfinitudeDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        InfinitudeHumidifierSensor(coordinator),
        InfinitudeOATSensor(coordinator),
        InfinitudeOperationStatusSensor(coordinator),
        InfinitudeSystemInfoSensor(coordinator),
    ]
    for zone in coordinator.data.get("zones", []):
        zid = zone["id"]
        entities.append(InfinitudeDamperSensor(coordinator, zid))
        entities.append(InfinitudeFanSensor(coordinator, zid))
    async_add_entities(entities)


class InfinitudeHumidifierSensor(CoordinatorEntity, SensorEntity):
    """System-level humidifier state sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:air-humidifier"

    def __init__(self, coordinator: InfinitudeDataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "infinitude_humidifier"
        self._attr_name = "Humidifier"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "system")},
            name="Infinitude System",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def available(self) -> bool:
        return super().available and not self.coordinator.data.get("stale", False)

    @property
    def native_value(self) -> str:
        on = self.coordinator.data.get("system", {}).get("humidifierOn", False)
        return "on" if on else "off"

    @property
    def icon(self) -> str:
        if self.native_value == "on":
            return "mdi:air-humidifier"
        return "mdi:air-humidifier-off"


class InfinitudeZoneSensor(CoordinatorEntity, SensorEntity):
    """Base class for Infinitude zone sensors."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: InfinitudeDataCoordinator, zone_id: str
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        zone = self._zone_data
        name = zone["name"] if zone else f"Zone {zone_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"zone_{zone_id}")},
            name=f"Infinitude {name}",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def _zone_data(self) -> dict | None:
        for z in self.coordinator.data.get("zones", []):
            if z["id"] == self._zone_id:
                return z
        return None

    @property
    def available(self) -> bool:
        return super().available and not self.coordinator.data.get("stale", False)


class InfinitudeDamperSensor(InfinitudeZoneSensor):
    """Damper position sensor for a zone."""

    _attr_icon = "mdi:valve"
    _attr_native_unit_of_measurement = "%"

    def __init__(
        self, coordinator: InfinitudeDataCoordinator, zone_id: str
    ) -> None:
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"infinitude_{zone_id}_damper"
        self._attr_name = "Damper position"

    @property
    def native_value(self) -> int | None:
        z = self._zone_data
        if z and z.get("damperPercent") is not None:
            return int(z["damperPercent"])
        return None


class InfinitudeFanSensor(InfinitudeZoneSensor):
    """Fan mode sensor for a zone."""

    _attr_icon = "mdi:fan"

    def __init__(
        self, coordinator: InfinitudeDataCoordinator, zone_id: str
    ) -> None:
        super().__init__(coordinator, zone_id)
        self._attr_unique_id = f"infinitude_{zone_id}_fan"
        self._attr_name = "Fan mode"

    @property
    def native_value(self) -> str | None:
        z = self._zone_data
        if z and z.get("fan"):
            return z["fan"]
        return None


class InfinitudeOATSensor(CoordinatorEntity, SensorEntity):
    """Outdoor air temperature sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:thermometer"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT

    def __init__(self, coordinator: InfinitudeDataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "infinitude_oat"
        self._attr_name = "Outdoor temperature"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "system")},
            name="Infinitude System",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def available(self) -> bool:
        return super().available and not self.coordinator.data.get("stale", False)

    @property
    def native_value(self) -> float | None:
        oat = self.coordinator.data.get("system", {}).get("outdoorTemperature")
        if oat is None:
            return None
        try:
            return float(oat)
        except (ValueError, TypeError):
            _LOGGER.warning("Invalid outdoor temperature value: '%s'", oat)
            return None


class InfinitudeOperationStatusSensor(CoordinatorEntity, SensorEntity):
    """Operation status message sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:information-outline"

    def __init__(self, coordinator: InfinitudeDataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "infinitude_op_status"
        self._attr_name = "Operation status"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "system")},
            name="Infinitude System",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def available(self) -> bool:
        return super().available and not self.coordinator.data.get("stale", False)

    @property
    def native_value(self) -> str | None:
        return (
            self.coordinator.data.get("system", {}).get("operatingStatusMessage")
            or None
        )


class InfinitudeSystemInfoSensor(CoordinatorEntity, SensorEntity):
    """System info sensor with schedule/profile data as attributes.

    JSON-encoded in the HVAC card's expected shape: schedule keyed by
    zone id then capitalized day name (matches shared.js DAYS); profiles
    as a list with string-valued setpoints (the card coerces to Number).
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:home-thermometer"

    def __init__(self, coordinator: InfinitudeDataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "infinitude_system_info"
        self._attr_name = "System info"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "system")},
            name="Infinitude System",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def available(self) -> bool:
        return super().available and not self.coordinator.data.get("stale", False)

    @property
    def native_value(self) -> str:
        return self.coordinator.data.get("system", {}).get("mode", "off")

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data
        profiles = []
        schedule_by_zone: dict[str, dict] = {}
        for z in data.get("zones", []):
            activities_legacy = {
                aid: {
                    "htsp": str(a["heat"]),
                    "clsp": str(a["cool"]),
                    "fan": a["fan"],
                }
                for aid, a in z.get("activities", {}).items()
            }
            profiles.append(
                {"id": z["id"], "name": z["name"], "activities": activities_legacy}
            )
            schedule_by_zone[z["id"]] = {
                day: [
                    {
                        "id": str(p["id"]),
                        "activity": p["activity"],
                        "time": p["time"],
                        "enabled": bool(p.get("enabled")),
                    }
                    for p in periods
                ]
                for day, periods in z.get("schedule", {}).items()
            }
        return {
            "host": data.get("host", ""),
            "carrier_ok": data.get("carrier_ok"),
            "schedule": json.dumps(schedule_by_zone),
            "profiles": json.dumps(profiles),
        }

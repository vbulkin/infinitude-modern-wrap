"""Sensor platform for Infinitude Direct — per-zone damper and fan sensors."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
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

    entities = []
    for zone in coordinator.data.get("zones", []):
        zid = zone["id"]
        entities.append(InfinitudeDamperSensor(coordinator, zid))
        entities.append(InfinitudeFanSensor(coordinator, zid))
    async_add_entities(entities)


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
        if z and z.get("damper"):
            return int(z["damper"])
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

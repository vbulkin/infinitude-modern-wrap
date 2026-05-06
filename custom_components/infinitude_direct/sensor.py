"""Sensor platform for Infinitude Direct."""

import json
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    REVOLUTIONS_PER_MINUTE,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)
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
        # alpha.37 — diagnostics from /v1/system/odu_status + idu_status
        # + energy. All gated on coordinator.data.get(<key>) is not None
        # so they report unavailable until the corresponding POST seeds.
        InfinitudeCompressorStageSensor(coordinator),
        InfinitudeCompressorRpmSensor(coordinator),
        InfinitudeSuctionPressureSensor(coordinator),
        InfinitudeDischargeTempSensor(coordinator),
        InfinitudeOduCoilTempSensor(coordinator),
        InfinitudeStaticPressureSensor(coordinator),
        InfinitudeIduBlowerRpmSensor(coordinator),
        InfinitudeIduAirflowSensor(coordinator),
        InfinitudeSeerSensor(coordinator),
        InfinitudeHspfSensor(coordinator),
        InfinitudeFaultCountSensor(coordinator),
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
            # alpha.36: surface the raw bridge-health status (one of
            # `healthy` / `degraded` / `unreachable` / `unknown` /
            # `disabled`) so the card maps to its 4-class palette
            # (ok/warn/err/unk) the same way the Infinitude dot
            # does. The legacy `carrier_ok` bool is kept for
            # backward-compat with anything reading the old shape.
            "carrier_status": data.get("carrier_status"),
            # alpha.30: live-event-stream connection state. The HVAC
            # card uses this to render a tri-state "Infinitude:
            # connected" indicator (green/yellow/red) rather than
            # the pre-SSE binary green-or-red.
            "sse_connected": data.get("sse_connected", False),
            "schedule": json.dumps(schedule_by_zone),
            "profiles": json.dumps(profiles),
        }


# ── Diagnostic sensors (alpha.37) ─────────────────────────────────────
# All read from coordinator.data slots seeded by `_get_obj_optional`
# fetches in `_async_update_data`. The slot is None until the
# thermostat POSTs the corresponding sub-resource — sensors
# `available` is False in that window so HA shows them as unavailable
# rather than emitting a stale or `unknown` state.


class _InfinitudeSystemSensor(CoordinatorEntity, SensorEntity):
    """Base for system-level diagnostic sensors that pull from a
    coordinator-data sub-dict (e.g. `odu_status`)."""

    _attr_has_entity_name = True
    _data_key: str = ""  # set by subclass: "odu_status" / "idu_status" / "energy" / "events"

    def __init__(self, coordinator: InfinitudeDataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "system")},
            name="Infinitude System",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def _data(self) -> dict | None:
        return self.coordinator.data.get(self._data_key)

    @property
    def available(self) -> bool:
        return (
            super().available
            and not self.coordinator.data.get("stale", False)
            and self._data is not None
        )


class InfinitudeCompressorStageSensor(_InfinitudeSystemSensor):
    """Outdoor-unit compressor stage (0/1/2) — answers "is the heat
    pump running on low or high capacity right now?".
    """
    _data_key = "odu_status"
    _attr_icon = "mdi:engine"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: InfinitudeDataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "infinitude_compressor_stage"
        self._attr_name = "Compressor stage"

    @property
    def native_value(self) -> int | None:
        d = self._data
        return d.get("operatingStage") if d else None

    @property
    def extra_state_attributes(self) -> dict:
        d = self._data or {}
        return {
            "raw_opstat": d.get("opstat"),
            "opmode": d.get("opmode"),
        }


class InfinitudeCompressorRpmSensor(_InfinitudeSystemSensor):
    _data_key = "odu_status"
    _attr_icon = "mdi:fan"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = REVOLUTIONS_PER_MINUTE

    def __init__(self, coordinator: InfinitudeDataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "infinitude_compressor_rpm"
        self._attr_name = "Compressor RPM"

    @property
    def native_value(self) -> int | None:
        d = self._data
        return d.get("compressorRpm") if d else None


class InfinitudeSuctionPressureSensor(_InfinitudeSystemSensor):
    _data_key = "odu_status"
    _attr_icon = "mdi:gauge"
    _attr_device_class = SensorDeviceClass.PRESSURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPressure.PSI

    def __init__(self, coordinator: InfinitudeDataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "infinitude_suction_pressure"
        self._attr_name = "Suction pressure"

    @property
    def native_value(self) -> float | None:
        d = self._data
        return d.get("suctionPressure") if d else None


class InfinitudeDischargeTempSensor(_InfinitudeSystemSensor):
    _data_key = "odu_status"
    _attr_icon = "mdi:thermometer"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT

    def __init__(self, coordinator: InfinitudeDataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "infinitude_discharge_temp"
        self._attr_name = "Discharge temperature"

    @property
    def native_value(self) -> int | None:
        d = self._data
        return d.get("dischargeTemperature") if d else None


class InfinitudeOduCoilTempSensor(_InfinitudeSystemSensor):
    _data_key = "odu_status"
    _attr_icon = "mdi:thermometer"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT

    def __init__(self, coordinator: InfinitudeDataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "infinitude_odu_coil_temp"
        self._attr_name = "Outdoor coil temperature"

    @property
    def native_value(self) -> int | None:
        d = self._data
        return d.get("coilTemperature") if d else None


class InfinitudeStaticPressureSensor(_InfinitudeSystemSensor):
    """Static pressure (in. WC) from the ODU report. Both ODU and
    IDU report this; ODU's reading is canonical for the install."""
    _data_key = "odu_status"
    _attr_icon = "mdi:gauge"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "inWC"

    def __init__(self, coordinator: InfinitudeDataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "infinitude_static_pressure"
        self._attr_name = "Static pressure"

    @property
    def native_value(self) -> float | None:
        d = self._data
        return d.get("staticPressure") if d else None


class InfinitudeIduBlowerRpmSensor(_InfinitudeSystemSensor):
    _data_key = "idu_status"
    _attr_icon = "mdi:fan"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = REVOLUTIONS_PER_MINUTE

    def __init__(self, coordinator: InfinitudeDataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "infinitude_idu_blower_rpm"
        self._attr_name = "Blower RPM"

    @property
    def native_value(self) -> int | None:
        d = self._data
        return d.get("blowerRpm") if d else None


class InfinitudeIduAirflowSensor(_InfinitudeSystemSensor):
    """Indoor airflow in CFM. Reported by both ODU and IDU; we use
    the IDU value since that's the directly-measured leg."""
    _data_key = "idu_status"
    _attr_icon = "mdi:weather-windy"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "ft³/min"

    def __init__(self, coordinator: InfinitudeDataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "infinitude_idu_airflow"
        self._attr_name = "Airflow"

    @property
    def native_value(self) -> int | None:
        d = self._data
        return d.get("iduCfm") if d else None


class InfinitudeSeerSensor(_InfinitudeSystemSensor):
    """SEER cooling-efficiency rating — static install config, never
    changes after commissioning. Surfaced for completeness alongside
    HSPF and as a label for cost-calculation automations."""
    _data_key = "energy"
    _attr_icon = "mdi:snowflake-thermometer"
    _attr_entity_category = None  # ratings are user-facing reference data, not diagnostic

    def __init__(self, coordinator: InfinitudeDataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "infinitude_seer"
        self._attr_name = "Cooling efficiency (SEER)"

    @property
    def native_value(self) -> float | None:
        d = self._data
        return d.get("seer") if d else None


class InfinitudeHspfSensor(_InfinitudeSystemSensor):
    """HSPF heating-efficiency rating — heat-pump-only metric."""
    _data_key = "energy"
    _attr_icon = "mdi:fire"

    def __init__(self, coordinator: InfinitudeDataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "infinitude_hspf"
        self._attr_name = "Heating efficiency (HSPF)"

    @property
    def native_value(self) -> float | None:
        d = self._data
        return d.get("hspf") if d else None


class InfinitudeFaultCountSensor(_InfinitudeSystemSensor):
    """Total recorded equipment events (active + cleared). The
    `binary_sensor.infinitude_fault_active` companion fires when
    any event is currently asserted; this counts the full history."""
    _data_key = "events"
    _attr_icon = "mdi:alert-circle-outline"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: InfinitudeDataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "infinitude_fault_count"
        self._attr_name = "Equipment events recorded"

    @property
    def native_value(self) -> int | None:
        d = self._data
        if d is None:
            return None
        return len(d.get("events", []))

    @property
    def extra_state_attributes(self) -> dict:
        d = self._data or {}
        events = d.get("events", []) or []
        return {
            "active_count": sum(1 for e in events if e.get("active")),
            "events": events[:20],  # truncate for state-attribute size
        }

"""Climate platform for Infinitude Direct."""

import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DEFAULT_COOL_SP,
    DEFAULT_HEAT_SP,
    DOMAIN,
    HA_TO_INFINITUDE_HVAC,
    INFINITUDE_TO_HA_HVAC,
    MANUFACTURER,
    MAX_COOL_TEMP,
    MAX_HEAT_TEMP,
    MIN_COOL_TEMP,
    MIN_HEAT_TEMP,
    MODEL,
    PRESET_MODES,
)
from .coordinator import InfinitudeDataCoordinator

_LOGGER = logging.getLogger(__name__)

_CONDITIONING_TO_ACTION = {
    "heating": HVACAction.HEATING,
    "cooling": HVACAction.COOLING,
    "dehumidifying": HVACAction.DRYING,
    "fan": HVACAction.FAN,
    "off": HVACAction.OFF,
    "idle": HVACAction.IDLE,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: InfinitudeDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        InfinitudeClimate(coordinator, zone["id"])
        for zone in coordinator.data.get("zones", [])
    ]
    async_add_entities(entities)


class InfinitudeClimate(CoordinatorEntity, ClimateEntity):
    """Climate entity for a single Infinitude zone."""

    _attr_has_entity_name = True
    _attr_translation_key = "infinitude_zone"
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.HEAT,
        HVACMode.COOL,
        HVACMode.HEAT_COOL,
        HVACMode.FAN_ONLY,
    ]
    _attr_preset_modes = PRESET_MODES
    _attr_min_temp = MIN_HEAT_TEMP
    _attr_max_temp = MAX_COOL_TEMP
    _attr_target_temperature_step = 1

    def __init__(
        self, coordinator: InfinitudeDataCoordinator, zone_id: str
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        zone = self._zone_data
        name = zone["name"] if zone else f"Zone {zone_id}"
        self._attr_unique_id = f"infinitude_{zone_id}"
        self._attr_name = None
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
    def _system_mode(self) -> str:
        return self.coordinator.data.get("system", {}).get("mode", "off")

    @property
    def available(self) -> bool:
        return super().available and not self.coordinator.data.get("stale", False)

    @property
    def supported_features(self) -> ClimateEntityFeature:
        features = ClimateEntityFeature.PRESET_MODE
        if self._system_mode == "auto":
            features |= ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        else:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE
        return features

    @property
    def current_temperature(self) -> float | None:
        z = self._zone_data
        if z and z.get("temperature") is not None:
            return float(z["temperature"])
        return None

    @property
    def current_humidity(self) -> int | None:
        z = self._zone_data
        if z and z.get("humidity") is not None:
            return int(z["humidity"])
        return None

    @property
    def target_temperature(self) -> float | None:
        z = self._zone_data
        if not z:
            return None
        mode = self._system_mode
        if mode == "heat" and z.get("heatSetpoint") is not None:
            return float(z["heatSetpoint"])
        if mode == "cool" and z.get("coolSetpoint") is not None:
            return float(z["coolSetpoint"])
        return None

    @property
    def target_temperature_high(self) -> float | None:
        z = self._zone_data
        if self._system_mode == "auto" and z and z.get("coolSetpoint") is not None:
            return float(z["coolSetpoint"])
        return None

    @property
    def target_temperature_low(self) -> float | None:
        z = self._zone_data
        if self._system_mode == "auto" and z and z.get("heatSetpoint") is not None:
            return float(z["heatSetpoint"])
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        ha_mode = INFINITUDE_TO_HA_HVAC.get(self._system_mode, "off")
        return HVACMode(ha_mode)

    @property
    def hvac_action(self) -> HVACAction:
        z = self._zone_data
        if not z:
            return HVACAction.OFF
        cond = z.get("conditioning", "idle")
        action = _CONDITIONING_TO_ACTION.get(cond, HVACAction.IDLE)
        if action == HVACAction.IDLE and self._system_mode == "off":
            return HVACAction.OFF
        return action

    @property
    def preset_mode(self) -> str | None:
        z = self._zone_data
        if not z:
            return None
        hold = z.get("hold") or {}
        if hold.get("active") and hold.get("activity"):
            return hold["activity"]
        return z.get("currentActivity")

    @property
    def extra_state_attributes(self) -> dict:
        attrs: dict = {}
        z = self._zone_data
        if z:
            if z.get("damperPercent") is not None:
                attrs["damper_position"] = int(z["damperPercent"])
            if z.get("fan"):
                attrs["fan_mode"] = z["fan"]
            hold = z.get("hold") or {}
            attrs["hold_active"] = bool(hold.get("active"))
            if hold.get("activity"):
                attrs["hold_activity"] = hold["activity"]
            if hold.get("until"):
                attrs["hold_until"] = hold["until"]
        system = self.coordinator.data.get("system", {})
        oat = system.get("outdoorTemperature")
        if oat is not None:
            attrs["outdoor_temperature"] = float(oat)
        wh = system.get("hold") or {}
        attrs["whole_house_hold_active"] = bool(wh.get("active"))
        if wh.get("activity"):
            attrs["whole_house_hold_activity"] = wh["activity"]
        if wh.get("until"):
            attrs["whole_house_hold_until"] = wh["until"]
        return attrs

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        inf_mode = HA_TO_INFINITUDE_HVAC.get(hvac_mode, "off")
        await self.coordinator.async_set_mode(inf_mode)
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs) -> None:
        z = self._zone_data
        if not z:
            _LOGGER.warning("set_temperature: zone %s data not available", self._zone_id)
            return

        current_htsp = int(z.get("heatSetpoint") or DEFAULT_HEAT_SP)
        current_clsp = int(z.get("coolSetpoint") or DEFAULT_COOL_SP)

        mode = self._system_mode

        if "target_temp_low" in kwargs and "target_temp_high" in kwargs:
            new_htsp = max(MIN_HEAT_TEMP, min(MAX_HEAT_TEMP, int(kwargs["target_temp_low"])))
            new_clsp = max(MIN_COOL_TEMP, min(MAX_COOL_TEMP, int(kwargs["target_temp_high"])))
        elif "temperature" in kwargs:
            temp = int(kwargs["temperature"])
            if mode == "heat":
                new_htsp = max(MIN_HEAT_TEMP, min(MAX_HEAT_TEMP, temp))
                new_clsp = current_clsp
            elif mode == "cool":
                new_htsp = current_htsp
                new_clsp = max(MIN_COOL_TEMP, min(MAX_COOL_TEMP, temp))
            else:
                new_htsp = max(MIN_HEAT_TEMP, min(MAX_HEAT_TEMP, temp))
                new_clsp = current_clsp
        else:
            return

        await self.coordinator.async_set_activity_temps(
            self._zone_id, "manual", new_htsp, new_clsp
        )
        await self.coordinator.async_set_hold(self._zone_id, "manual", "auto")
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode in PRESET_MODES:
            await self.coordinator.async_set_hold(
                self._zone_id, preset_mode, "forever"
            )
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.warning("set_preset_mode: unknown preset '%s'", preset_mode)

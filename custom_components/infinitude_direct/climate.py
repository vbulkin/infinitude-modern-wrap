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
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    HA_TO_INFINITUDE_HVAC,
    INFINITUDE_TO_HA_HVAC,
    PRESET_MODES,
)
from .coordinator import InfinitudeDataCoordinator

_LOGGER = logging.getLogger(__name__)


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
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.HEAT,
        HVACMode.COOL,
        HVACMode.HEAT_COOL,
    ]
    _attr_preset_modes = PRESET_MODES
    _attr_min_temp = 50
    _attr_max_temp = 99
    _attr_target_temperature_step = 1

    def __init__(
        self, coordinator: InfinitudeDataCoordinator, zone_id: str
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        zone = self._zone_data
        name = zone["name"] if zone else f"Zone {zone_id}"
        self._attr_unique_id = f"infinitude_{zone_id}"
        self._attr_name = name

    @property
    def _zone_data(self) -> dict | None:
        for z in self.coordinator.data.get("zones", []):
            if z["id"] == self._zone_id:
                return z
        return None

    @property
    def supported_features(self) -> ClimateEntityFeature:
        features = ClimateEntityFeature.PRESET_MODE
        mode = self.coordinator.data.get("mode", "off")
        if mode in ("auto", "heatcool"):
            features |= ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        else:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE
        return features

    @property
    def current_temperature(self) -> float | None:
        z = self._zone_data
        if z and z.get("temp"):
            return float(z["temp"])
        return None

    @property
    def current_humidity(self) -> int | None:
        z = self._zone_data
        if z and z.get("rh"):
            return int(z["rh"])
        return None

    @property
    def target_temperature(self) -> float | None:
        z = self._zone_data
        if not z:
            return None
        mode = self.coordinator.data.get("mode", "off")
        if mode == "heat" and z.get("htsp"):
            return float(z["htsp"])
        if mode == "cool" and z.get("clsp"):
            return float(z["clsp"])
        return None

    @property
    def target_temperature_high(self) -> float | None:
        z = self._zone_data
        mode = self.coordinator.data.get("mode", "off")
        if mode in ("auto", "heatcool") and z and z.get("clsp"):
            return float(z["clsp"])
        return None

    @property
    def target_temperature_low(self) -> float | None:
        z = self._zone_data
        mode = self.coordinator.data.get("mode", "off")
        if mode in ("auto", "heatcool") and z and z.get("htsp"):
            return float(z["htsp"])
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        mode = self.coordinator.data.get("mode", "off")
        ha_mode = INFINITUDE_TO_HA_HVAC.get(mode, "off")
        return HVACMode(ha_mode)

    @property
    def hvac_action(self) -> HVACAction:
        z = self._zone_data
        if not z:
            return HVACAction.OFF
        cond = z.get("conditioning", "idle")
        if cond == "active_heat":
            return HVACAction.HEATING
        if cond == "active_cool":
            return HVACAction.COOLING
        if "dehum" in cond:
            return HVACAction.DRYING
        mode = self.coordinator.data.get("mode", "off")
        if mode == "off":
            return HVACAction.OFF
        return HVACAction.IDLE

    @property
    def preset_mode(self) -> str | None:
        z = self._zone_data
        if not z:
            return None
        if z.get("hold") and z.get("holdActivity"):
            return z["holdActivity"]
        return z.get("currentActivity")

    @property
    def extra_state_attributes(self) -> dict:
        attrs = {}
        z = self._zone_data
        if z:
            if z.get("damper"):
                attrs["damper_position"] = z["damper"]
            if z.get("fan"):
                attrs["fan_mode"] = z["fan"]
            attrs["hold_active"] = z.get("hold", False)
            if z.get("holdActivity"):
                attrs["hold_activity"] = z["holdActivity"]
        oat = self.coordinator.data.get("oat")
        if oat:
            attrs["outdoor_temperature"] = float(oat)
        return attrs

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        inf_mode = HA_TO_INFINITUDE_HVAC.get(hvac_mode, "off")
        await self.coordinator.async_set_mode(inf_mode)
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs) -> None:
        z = self._zone_data
        if not z:
            return

        current_htsp = int(float(z.get("htsp") or 68))
        current_clsp = int(float(z.get("clsp") or 76))

        mode = self.coordinator.data.get("mode", "off")

        if "target_temp_low" in kwargs and "target_temp_high" in kwargs:
            new_htsp = int(kwargs["target_temp_low"])
            new_clsp = int(kwargs["target_temp_high"])
        elif "temperature" in kwargs:
            temp = int(kwargs["temperature"])
            if mode == "heat":
                new_htsp = temp
                new_clsp = current_clsp
            elif mode == "cool":
                new_htsp = current_htsp
                new_clsp = temp
            else:
                new_htsp = temp
                new_clsp = current_clsp
        else:
            return

        await self.coordinator.async_set_activity_temps(
            self._zone_id, "manual", new_htsp, new_clsp
        )
        await self.coordinator.async_set_hold(
            self._zone_id, "manual", "nextTransition"
        )
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode in PRESET_MODES:
            await self.coordinator.async_set_hold(
                self._zone_id, preset_mode, "forever"
            )
            await self.coordinator.async_request_refresh()

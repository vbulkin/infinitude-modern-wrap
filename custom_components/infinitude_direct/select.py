"""Select platform for Infinitude Direct — Whole House Hold."""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PRESET_MODES
from .coordinator import InfinitudeDataCoordinator

_LOGGER = logging.getLogger(__name__)

OPTION_OFF = "off"
OPTIONS = [OPTION_OFF] + PRESET_MODES


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: InfinitudeDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([InfinitudeWholeHouseHoldSelect(coordinator)])


class InfinitudeWholeHouseHoldSelect(CoordinatorEntity, SelectEntity):
    """Select entity to control the whole house hold."""

    _attr_has_entity_name = True
    _attr_name = "Whole house hold"
    _attr_icon = "mdi:home-lock"
    _attr_options = OPTIONS

    def __init__(self, coordinator: InfinitudeDataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "infinitude_whole_house_hold"

    @property
    def current_option(self) -> str:
        wh = self.coordinator.data.get("whole_house_hold", {})
        if wh.get("hold") and wh.get("holdActivity"):
            return wh["holdActivity"]
        return OPTION_OFF

    @property
    def extra_state_attributes(self) -> dict:
        wh = self.coordinator.data.get("whole_house_hold", {})
        attrs = {}
        if wh.get("otmr"):
            attrs["hold_until"] = wh["otmr"]
        return attrs

    async def async_select_option(self, option: str) -> None:
        if option == OPTION_OFF:
            await self.coordinator.async_cancel_whole_house_hold()
        else:
            await self.coordinator.async_set_whole_house_hold(option)
        await self.coordinator.async_request_refresh()

"""Config flow for Infinitude Direct."""

import logging

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_HOST, DEFAULT_HOST, DOMAIN

_LOGGER = logging.getLogger(__name__)


class InfinitudeDirectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Infinitude Direct."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST].rstrip("/")
            session = async_get_clientsession(self.hass)
            try:
                resp = await session.get(
                    f"{host}/status.json", timeout=aiohttp.ClientTimeout(total=10)
                )
                resp.raise_for_status()
                data = await resp.json(content_type=None)
                if "status" not in data:
                    errors["base"] = "invalid_response"
                else:
                    await self.async_set_unique_id(f"{DOMAIN}_{host}")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title="Infinitude",
                        data={CONF_HOST: host},
                    )
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during config flow")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                }
            ),
            errors=errors,
        )

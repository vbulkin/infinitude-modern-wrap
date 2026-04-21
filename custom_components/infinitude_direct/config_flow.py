"""Config flow for Infinitude Direct."""

import logging

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_HOST, DEFAULT_HOST, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def _validate_connection(session, host: str) -> str | None:
    """Test the connection to an Infinitude proxy.

    Hits `/v1/healthz` on the Python add-on. Returns an error key string
    on failure, or None on success.
    """
    try:
        resp = await session.get(
            f"{host}/v1/healthz", timeout=aiohttp.ClientTimeout(total=10)
        )
        resp.raise_for_status()
        data = await resp.json(content_type=None)
        if "components" not in data or "status" not in data:
            return "invalid_response"
    except aiohttp.ClientError:
        return "cannot_connect"
    except Exception:
        _LOGGER.exception("Unexpected error validating connection to %s", host)
        return "unknown"
    return None


class InfinitudeDirectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Infinitude Direct."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        return InfinitudeOptionsFlow()

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST].rstrip("/")
            session = async_get_clientsession(self.hass)
            error = await _validate_connection(session, host)
            if error:
                errors["base"] = error
            else:
                await self.async_set_unique_id(f"{DOMAIN}_{host}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Infinitude",
                    data={CONF_HOST: host},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                }
            ),
            errors=errors,
        )


class InfinitudeOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Infinitude Direct (change host URL)."""

    async def async_step_init(self, user_input=None):
        errors = {}
        current_host = self.config_entry.data.get(CONF_HOST, DEFAULT_HOST)

        if user_input is not None:
            host = user_input[CONF_HOST].rstrip("/")
            session = async_get_clientsession(self.hass)
            error = await _validate_connection(session, host)
            if error:
                errors["base"] = error
            else:
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data={**self.config_entry.data, CONF_HOST: host}
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=current_host): str,
                }
            ),
            errors=errors,
        )

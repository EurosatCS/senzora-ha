"""Config flow for Eurosat Meters."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_API_KEY
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    EurosatApiClient,
    EurosatApiError,
    EurosatAuthError,
    EurosatRateLimitError,
)
from .const import (
    CONF_GROUP_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Optional(CONF_GROUP_ID): vol.All(vol.Coerce(int), vol.Range(min=1)),
    }
)
REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): str})


def _account_id(api_key: str) -> str:
    """Stable, non-secret identifier of the account behind a key."""
    prefix = api_key.split(";", 1)[0]
    if ";" in api_key and prefix.isdigit():
        return prefix
    return hashlib.sha256(api_key.encode()).hexdigest()[:12]


class EurosatConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for the API key and verify it with one request."""

    VERSION = 1

    async def _validate(self, api_key: str, group_id: int | None) -> str | None:
        client = EurosatApiClient(
            async_get_clientsession(self.hass), api_key, group_id
        )
        try:
            await client.async_get_last_data()
        except EurosatAuthError:
            return "invalid_auth"
        except EurosatRateLimitError:
            return "rate_limited"
        except EurosatApiError:
            return "cannot_connect"
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            group_id = user_input.get(CONF_GROUP_ID)
            account = _account_id(api_key)
            await self.async_set_unique_id(f"{account}_{group_id or 'home'}")
            self._abort_if_unique_id_configured()

            if (error := await self._validate(api_key, group_id)) is None:
                data: dict[str, Any] = {CONF_API_KEY: api_key}
                title = f"Eurosat {account}"
                if group_id:
                    data[CONF_GROUP_ID] = group_id
                    title += f" / {group_id}"
                return self.async_create_entry(title=title, data=data)
            errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                USER_SCHEMA, user_input or {}
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            error = await self._validate(api_key, entry.data.get(CONF_GROUP_ID))
            if error is None:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_API_KEY: api_key}
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=REAUTH_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return EurosatOptionsFlow()


class EurosatOptionsFlow(OptionsFlow):
    """Let the user change the polling interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    )
                }
            ),
        )

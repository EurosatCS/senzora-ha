"""Eurosat Meters: water / energy meter readings from the Eurosat REST API."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EurosatApiClient
from .const import CONF_GROUP_ID
from .coordinator import EurosatCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

type EurosatConfigEntry = ConfigEntry[EurosatCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: EurosatConfigEntry) -> bool:
    """Set up Eurosat Meters from a config entry."""
    client = EurosatApiClient(
        async_get_clientsession(hass),
        entry.data[CONF_API_KEY],
        entry.data.get(CONF_GROUP_ID),
    )
    coordinator = EurosatCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_options))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EurosatConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_on_options(
    hass: HomeAssistant, entry: EurosatConfigEntry
) -> None:
    await hass.config_entries.async_reload(entry.entry_id)

"""Data update coordinator for Eurosat Meters."""

from __future__ import annotations

from datetime import timedelta
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EurosatApiClient, EurosatApiError, EurosatAuthError
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

TITLES_REFRESH_SECONDS = 24 * 3600


class EurosatCoordinator(DataUpdateCoordinator[dict[int, dict[str, Any]]]):
    """Polls lastData once per interval; data is keyed by meter_id."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: EurosatApiClient
    ) -> None:
        minutes = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=minutes),
        )
        self.client = client
        self.titles: dict[int, str] = {}
        self._titles_fetched: float = 0.0

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        try:
            rows = await self.client.async_get_last_data()
        except EurosatAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except EurosatApiError as err:
            raise UpdateFailed(str(err)) from err

        # Meter labels are optional and rarely change: refresh once a day.
        if time.monotonic() - self._titles_fetched > TITLES_REFRESH_SECONDS or (
            not self._titles_fetched
        ):
            self._titles_fetched = time.monotonic()
            try:
                self.titles = await self.client.async_get_meter_titles()
            except EurosatApiError as err:
                _LOGGER.debug("Could not load meter labels: %s", err)

        return {
            row["meter_id"]: row
            for row in rows
            if isinstance(row.get("meter_id"), int)
        }

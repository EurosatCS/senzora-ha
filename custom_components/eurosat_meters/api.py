"""Minimal async client for the Eurosat (Electronic Log Book) meter API."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from .const import BASE_URL, PATH_LAST_DATA, PATH_METER_LIST

TIMEOUT = aiohttp.ClientTimeout(total=30)


class EurosatApiError(Exception):
    """Generic API error."""


class EurosatAuthError(EurosatApiError):
    """API key rejected (HTTP 401/403)."""


class EurosatRateLimitError(EurosatApiError):
    """Too many requests (HTTP 429)."""


class EurosatApiClient:
    """Thin wrapper around the endpoints the integration needs."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        group_id: int | None = None,
    ) -> None:
        self._session = session
        self._api_key = api_key
        self._group_id = group_id

    async def _get(self, path: str) -> list[dict[str, Any]]:
        params = {"group_id": self._group_id} if self._group_id else None
        try:
            async with self._session.get(
                f"{BASE_URL}{path}",
                headers={"X-API-KEY": self._api_key, "Accept": "application/json"},
                params=params,
                timeout=TIMEOUT,
            ) as resp:
                if resp.status in (401, 403):
                    raise EurosatAuthError(f"API key rejected (HTTP {resp.status})")
                if resp.status == 429:
                    retry = resp.headers.get("Retry-After", "?")
                    raise EurosatRateLimitError(
                        f"Rate limit exceeded, retry after {retry} s"
                    )
                if resp.status >= 400:
                    raise EurosatApiError(f"Unexpected response HTTP {resp.status}")
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            raise EurosatApiError(f"Error communicating with API: {err}") from err

        if not isinstance(data, list):
            raise EurosatApiError("Unexpected response format (expected a list)")
        return [item for item in data if isinstance(item, dict)]

    async def async_get_last_data(self) -> list[dict[str, Any]]:
        """Return the last cached value of every meter (up to 31 days old)."""
        return await self._get(PATH_LAST_DATA)

    async def async_get_meter_titles(self) -> dict[int, str]:
        """Return {meter_id: title} for meters that have a label."""
        titles: dict[int, str] = {}
        for meter in await self._get(PATH_METER_LIST):
            title = str(meter.get("title") or "").strip()
            if title and isinstance(meter.get("id"), int):
                titles[meter["id"]] = title
        return titles

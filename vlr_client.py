from __future__ import annotations

from typing import Any

import aiohttp


class VLRClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": "ValorantDiscordBot/1.0"},
            )

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._session is None:
            await self.start()
        assert self._session is not None

        url = f"{self.base_url}{path}"
        async with self._session.get(url, params=params) as resp:
            resp.raise_for_status()
            payload = await resp.json()
            if payload.get("status") != "success":
                raise RuntimeError(f"API error from {path}: {payload}")
            return payload.get("data", {})

    async def health(self) -> dict[str, Any]:
        return await self._get("/v2/health")

    async def news(self) -> list[dict[str, Any]]:
        data = await self._get("/v2/news")
        return data.get("segments", [])

    async def matches(self, query: str) -> list[dict[str, Any]]:
        data = await self._get("/v2/match", params={"q": query})
        return data.get("segments", [])

    async def match_details(self, match_id: str) -> dict[str, Any]:
        data = await self._get("/v2/match/details", params={"match_id": match_id})
        segments = data.get("segments")
        if isinstance(segments, list) and segments:
            return segments[0]
        if isinstance(segments, dict):
            return segments
        return data

    @staticmethod
    def extract_match_id(match_page: str) -> str | None:
        if not match_page:
            return None
        # URLs look like https://www.vlr.gg/595657/... or /595657/...
        parts = match_page.rstrip("/").split("/")
        for part in reversed(parts):
            if part.isdigit():
                return part
        return None

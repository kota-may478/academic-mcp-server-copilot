from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from academic_mcp_server.common.cache import TTLCache
from academic_mcp_server.common.config import AppConfig
from academic_mcp_server.common.models import Paper, PaperSearchResponse
from academic_mcp_server.common.normalize import normalize_crossref_work, normalize_limit


class CrossrefConnector:
    """Async client for Crossref REST API."""

    _SELECT_FIELDS = (
        "DOI,title,author,published-print,published-online,issued,created,"
        "container-title,abstract,URL,is-referenced-by-count,subject"
    )

    def __init__(self, config: AppConfig) -> None:
        self._default_limit = config.default_limit
        self._contact_email = config.contact_email
        self._cache: TTLCache[PaperSearchResponse | Paper] = TTLCache(config.cache_ttl_seconds)
        self._client = httpx.AsyncClient(
            base_url="https://api.crossref.org",
            headers=config.crossref_headers,
            timeout=config.request_timeout_seconds,
        )

    async def aclose(self) -> None:
        await self._client.aclose()
        self._cache.clear()

    async def search_works(self, query: str, limit: int | None = None) -> PaperSearchResponse:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query must not be empty.")

        normalized_limit = normalize_limit(limit, default=self._default_limit, maximum=20)
        cache_key = f"search:{normalized_query}:{normalized_limit}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, PaperSearchResponse):
            return cached

        message = await self._get_message(
            "/works",
            params={
                "query": normalized_query,
                "rows": normalized_limit,
                "select": self._SELECT_FIELDS,
                "mailto": self._contact_email,
            },
        )
        result = PaperSearchResponse(
            source="crossref",
            query=normalized_query,
            limit=normalized_limit,
            total=message.get("total-results"),
            items=[
                normalize_crossref_work(item)
                for item in message.get("items") or []
            ],
        )
        self._cache.set(cache_key, result)
        return result

    async def get_work_by_doi(self, doi: str) -> Paper:
        normalized_doi = doi.strip()
        if not normalized_doi:
            raise ValueError("doi must not be empty.")

        cache_key = f"work:{normalized_doi.lower()}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, Paper):
            return cached

        message = await self._get_message(
            f"/works/{quote(normalized_doi, safe='')}",
            params={"mailto": self._contact_email},
        )
        result = normalize_crossref_work(message)
        self._cache.set(cache_key, result)
        return result

    async def _get_message(self, path: str, *, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._client.get(path, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(self._format_http_error(exc)) from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Crossref request failed: {exc}") from exc

        payload = response.json()
        return payload.get("message") or {}

    @staticmethod
    def _format_http_error(exc: httpx.HTTPStatusError) -> str:
        response = exc.response
        detail: str | None = None
        try:
            payload = response.json()
            if isinstance(payload, dict):
                message = payload.get("message")
                if isinstance(message, dict):
                    detail = str(message.get("message") or "").strip() or None
                else:
                    detail = str(message or "").strip() or None
        except ValueError:
            detail = None

        base_message = f"Crossref returned HTTP {response.status_code}."
        if detail:
            return f"{base_message} {detail}"
        return base_message
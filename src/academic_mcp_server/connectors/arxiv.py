from __future__ import annotations

import asyncio
import time
from typing import Any

import feedparser
import httpx

from academic_mcp_server.common.cache import TTLCache
from academic_mcp_server.common.config import AppConfig
from academic_mcp_server.common.models import Paper, PaperSearchResponse
from academic_mcp_server.common.normalize import coerce_int, normalize_arxiv_entry, normalize_limit


class ArxivConnector:
    """Async client for arXiv Atom API with serialized rate limiting."""

    def __init__(self, config: AppConfig) -> None:
        self._default_limit = config.default_limit
        self._cache: TTLCache[Any] = TTLCache(config.cache_ttl_seconds)
        self._client = httpx.AsyncClient(
            base_url="https://export.arxiv.org",
            headers={"Accept": "application/atom+xml"},
            limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
            timeout=config.request_timeout_seconds,
        )
        self._request_lock = asyncio.Lock()
        self._last_request_finished_at = 0.0
        self._minimum_interval_seconds = 3.0

    async def aclose(self) -> None:
        await self._client.aclose()
        self._cache.clear()

    async def search(self, query: str, limit: int | None = None) -> PaperSearchResponse:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query must not be empty.")

        normalized_limit = normalize_limit(limit, default=self._default_limit, maximum=20)
        cache_key = f"search:{normalized_query}:{normalized_limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        feed = await self._get_feed(
            params={
                "search_query": f"all:{normalized_query}",
                "start": 0,
                "max_results": normalized_limit,
                "sortBy": "relevance",
                "sortOrder": "descending",
            }
        )
        result = PaperSearchResponse(
            source="arxiv",
            query=normalized_query,
            limit=normalized_limit,
            total=coerce_int(feed.feed.get("opensearch_totalresults")),
            items=[normalize_arxiv_entry(entry) for entry in feed.entries],
        )
        self._cache.set(cache_key, result)
        return result

    async def get_paper(self, arxiv_id: str) -> Paper:
        normalized_identifier = self._normalize_identifier(arxiv_id)
        cache_key = f"paper:{normalized_identifier}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, Paper):
            return cached

        feed = await self._get_feed(params={"id_list": normalized_identifier})
        if not feed.entries:
            raise RuntimeError(f"arXiv paper '{normalized_identifier}' was not found.")

        result = normalize_arxiv_entry(feed.entries[0])
        self._cache.set(cache_key, result)
        return result

    async def _get_feed(self, *, params: dict[str, Any]) -> feedparser.FeedParserDict:
        async with self._request_lock:
            wait_seconds = self._minimum_interval_seconds - (
                time.monotonic() - self._last_request_finished_at
            )
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)

            try:
                response = await self._client.get("/api/query", params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise RuntimeError(
                    f"arXiv returned HTTP {exc.response.status_code}."
                ) from exc
            except httpx.HTTPError as exc:
                raise RuntimeError(f"arXiv request failed: {exc}") from exc
            finally:
                self._last_request_finished_at = time.monotonic()

        feed = feedparser.parse(response.text)
        if getattr(feed, "bozo", 0):
            bozo_exception = getattr(feed, "bozo_exception", None)
            if bozo_exception is not None:
                raise RuntimeError(f"arXiv feed parsing failed: {bozo_exception}")

        return feed

    @staticmethod
    def _normalize_identifier(arxiv_id: str) -> str:
        normalized_identifier = arxiv_id.strip()
        if not normalized_identifier:
            raise ValueError("arxiv_id must not be empty.")

        lowered = normalized_identifier.lower()
        if lowered.startswith("arxiv:"):
            return normalized_identifier.split(":", 1)[1]
        if "/abs/" in lowered:
            return normalized_identifier.rsplit("/", 1)[-1]
        if "/pdf/" in lowered:
            return normalized_identifier.rsplit("/", 1)[-1].removesuffix(".pdf")

        return normalized_identifier
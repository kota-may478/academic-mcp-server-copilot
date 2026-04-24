from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from academic_mcp_server.common.cache import TTLCache
from academic_mcp_server.common.config import AppConfig
from academic_mcp_server.common.models import Paper, PaperSearchResponse
from academic_mcp_server.common.normalize import normalize_limit, normalize_semantic_scholar_paper


class SemanticScholarConnector:
    """Async client for Semantic Scholar Graph API."""

    _SEARCH_FIELDS = (
        "paperId,title,abstract,authors,year,publicationDate,venue,url,"
        "externalIds,citationCount,openAccessPdf,fieldsOfStudy"
    )

    def __init__(self, config: AppConfig) -> None:
        self._default_limit = config.default_limit
        self._cache: TTLCache[PaperSearchResponse | Paper] = TTLCache(config.cache_ttl_seconds)
        self._client = httpx.AsyncClient(
            base_url="https://api.semanticscholar.org/graph/v1",
            headers=config.semantic_scholar_headers,
            timeout=config.request_timeout_seconds,
        )

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
        if isinstance(cached, PaperSearchResponse):
            return cached

        payload = await self._get_json(
            "/paper/search",
            params={
                "query": normalized_query,
                "limit": normalized_limit,
                "fields": self._SEARCH_FIELDS,
            },
        )
        result = PaperSearchResponse(
            source="semantic_scholar",
            query=normalized_query,
            limit=normalized_limit,
            total=payload.get("total"),
            items=[
                normalize_semantic_scholar_paper(item)
                for item in payload.get("data") or []
            ],
        )
        self._cache.set(cache_key, result)
        return result

    async def get_paper(self, paper_id: str) -> Paper:
        normalized_identifier = self._normalize_identifier(paper_id)
        cache_key = f"paper:{normalized_identifier}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, Paper):
            return cached

        payload = await self._get_json(
            f"/paper/{quote(normalized_identifier, safe='')}",
            params={"fields": self._SEARCH_FIELDS},
        )
        result = normalize_semantic_scholar_paper(payload)
        self._cache.set(cache_key, result)
        return result

    async def _get_json(self, path: str, *, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._client.get(path, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(self._format_http_error(exc)) from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Semantic Scholar request failed: {exc}") from exc

        return response.json()

    @staticmethod
    def _normalize_identifier(paper_id: str) -> str:
        normalized_identifier = paper_id.strip()
        if not normalized_identifier:
            raise ValueError("paper_id must not be empty.")

        lowered = normalized_identifier.lower()
        if lowered.startswith(("doi:", "corpusid:", "arxiv:", "acl:", "pmid:", "pmcid:")):
            return normalized_identifier

        if normalized_identifier.startswith("10."):
            return f"DOI:{normalized_identifier}"

        return normalized_identifier

    @staticmethod
    def _format_http_error(exc: httpx.HTTPStatusError) -> str:
        response = exc.response
        detail: str | None = None
        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = str(payload.get("error") or payload.get("message") or "").strip() or None
        except ValueError:
            detail = None

        base_message = f"Semantic Scholar returned HTTP {response.status_code}."
        if detail:
            return f"{base_message} {detail}"
        return base_message
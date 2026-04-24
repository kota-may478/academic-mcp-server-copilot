from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote

import httpx

from academic_mcp_server.common.cache import TTLCache
from academic_mcp_server.common.config import AppConfig
from academic_mcp_server.common.models import Author, AuthorCollectionResponse, Paper, PaperCollectionResponse, PaperSearchResponse
from academic_mcp_server.common.normalize import normalize_limit, normalize_offset, normalize_semantic_scholar_author, normalize_semantic_scholar_paper


LOGGER = logging.getLogger(__name__)


class SemanticScholarConnector:
    """Async client for Semantic Scholar Graph API."""

    _SEMANTIC_SCHOLAR_PAPER_ID_PATTERN = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)

    _PAPER_FIELDS = (
        "paperId,corpusId,title,abstract,authors,year,publicationDate,venue,url,"
        "externalIds,citationCount,referenceCount,influentialCitationCount,isOpenAccess,"
        "openAccessPdf,fieldsOfStudy,s2FieldsOfStudy,publicationTypes,publicationVenue,"
        "journal,tldr,textAvailability"
    )
    _RECOMMENDATION_FIELDS = (
        "paperId,corpusId,title,abstract,authors,year,publicationDate,venue,url,"
        "externalIds,citationCount,referenceCount,influentialCitationCount,isOpenAccess,"
        "openAccessPdf,fieldsOfStudy,s2FieldsOfStudy,publicationTypes,publicationVenue,"
        "journal"
    )
    _RELATION_PAPER_FIELDS = _RECOMMENDATION_FIELDS
    _AUTHOR_FIELDS = (
        "name,url,homepage,affiliations,paperCount,citationCount,hIndex,externalIds"
    )
    _RELATION_FIELDS = f"contexts,intents,isInfluential,{_RELATION_PAPER_FIELDS}"

    def __init__(self, config: AppConfig) -> None:
        self._default_limit = config.default_limit
        self._cache: TTLCache[Any] = TTLCache(config.cache_ttl_seconds)
        self._request_lock = asyncio.Lock()
        self._last_request_started_at = 0.0
        self._minimum_interval_seconds = 1.0
        self._jitter_max_seconds = 0.5
        self._initial_retry_delay_seconds = 2.0
        self._max_retry_delay_seconds = 30.0
        self._max_retry_attempts = 5
        self._graph_client = httpx.AsyncClient(
            base_url="https://api.semanticscholar.org/graph/v1",
            headers=config.semantic_scholar_headers,
            timeout=config.request_timeout_seconds,
        )
        self._recommendations_client = httpx.AsyncClient(
            base_url="https://api.semanticscholar.org/recommendations/v1",
            headers=config.semantic_scholar_headers,
            timeout=config.request_timeout_seconds,
        )

    async def aclose(self) -> None:
        await self._graph_client.aclose()
        await self._recommendations_client.aclose()
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
            self._graph_client,
            "/paper/search",
            params={
                "query": normalized_query,
                "limit": normalized_limit,
                "fields": self._PAPER_FIELDS,
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
        self._cache_papers(result.items)
        self._cache.set(cache_key, result)
        return result

    async def get_paper(self, paper_id: str) -> Paper:
        normalized_identifier = self._normalize_identifier(paper_id)
        cache_key = f"paper:{normalized_identifier}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, Paper):
            return cached

        payload = await self._get_json(
            self._graph_client,
            f"/paper/{quote(normalized_identifier, safe='')}",
            params={"fields": self._PAPER_FIELDS},
        )
        result = normalize_semantic_scholar_paper(payload)
        self._cache.set(cache_key, result)
        return result

    async def get_papers_batch(self, paper_ids: list[str]) -> PaperCollectionResponse:
        normalized_identifiers = self._normalize_identifier_list(paper_ids, maximum=500)
        cache_key = f"paper_batch:{','.join(normalized_identifiers)}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, PaperCollectionResponse):
            return cached

        payload = await self._post_json(
            self._graph_client,
            "/paper/batch",
            params={"fields": self._PAPER_FIELDS},
            json_body={"ids": normalized_identifiers},
        )
        result = PaperCollectionResponse(
            source="semantic_scholar",
            kind="paper_batch",
            identifier=",".join(normalized_identifiers),
            total=len(payload),
            items=[normalize_semantic_scholar_paper(item) for item in payload if isinstance(item, dict)],
        )
        self._cache_papers(result.items)
        self._cache.set(cache_key, result)
        return result

    async def get_citations(
        self,
        paper_id: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> PaperCollectionResponse:
        return await self._get_relation_collection(
            kind="citations",
            paper_id=paper_id,
            relation_path="citations",
            relation_key="citingPaper",
            limit=limit,
            offset=offset,
        )

    async def get_references(
        self,
        paper_id: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> PaperCollectionResponse:
        return await self._get_relation_collection(
            kind="references",
            paper_id=paper_id,
            relation_path="references",
            relation_key="citedPaper",
            limit=limit,
            offset=offset,
        )

    async def search_authors(
        self,
        query: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> AuthorCollectionResponse:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query must not be empty.")

        normalized_limit = normalize_limit(limit, default=self._default_limit, maximum=100)
        normalized_offset = normalize_offset(offset)
        cache_key = f"author_search:{normalized_query}:{normalized_limit}:{normalized_offset}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, AuthorCollectionResponse):
            return cached

        payload = await self._get_json(
            self._graph_client,
            "/author/search",
            params={
                "query": normalized_query,
                "limit": normalized_limit,
                "offset": normalized_offset,
                "fields": self._AUTHOR_FIELDS,
            },
        )
        result = AuthorCollectionResponse(
            source="semantic_scholar",
            kind="author_search",
            query=normalized_query,
            limit=normalized_limit,
            offset=payload.get("offset", normalized_offset),
            next_offset=payload.get("next"),
            total=payload.get("total"),
            items=[
                normalize_semantic_scholar_author(item)
                for item in payload.get("data") or []
            ],
        )
        self._cache.set(cache_key, result)
        return result

    async def get_author(self, author_id: str) -> Author:
        normalized_identifier = self._normalize_simple_identifier(author_id, label="author_id")
        cache_key = f"author:{normalized_identifier}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, Author):
            return cached

        payload = await self._get_json(
            self._graph_client,
            f"/author/{quote(normalized_identifier, safe='')}",
            params={"fields": self._AUTHOR_FIELDS},
        )
        result = normalize_semantic_scholar_author(payload)
        self._cache.set(cache_key, result)
        return result

    async def get_author_papers(
        self,
        author_id: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> PaperCollectionResponse:
        normalized_identifier = self._normalize_simple_identifier(author_id, label="author_id")
        normalized_limit = normalize_limit(limit, default=self._default_limit, maximum=100)
        normalized_offset = normalize_offset(offset)
        cache_key = f"author_papers:{normalized_identifier}:{normalized_limit}:{normalized_offset}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, PaperCollectionResponse):
            return cached

        payload = await self._get_json(
            self._graph_client,
            f"/author/{quote(normalized_identifier, safe='')}/papers",
            params={
                "limit": normalized_limit,
                "offset": normalized_offset,
                "fields": self._PAPER_FIELDS,
            },
        )
        result = PaperCollectionResponse(
            source="semantic_scholar",
            kind="author_papers",
            identifier=normalized_identifier,
            limit=normalized_limit,
            offset=payload.get("offset", normalized_offset),
            next_offset=payload.get("next"),
            items=[
                normalize_semantic_scholar_paper(item)
                for item in payload.get("data") or []
            ],
        )
        self._cache_papers(result.items)
        self._cache.set(cache_key, result)
        return result

    async def get_recommended_papers(
        self,
        paper_id: str,
        *,
        limit: int | None = None,
        pool: str = "recent",
    ) -> PaperCollectionResponse:
        normalized_identifier = await self._resolve_relation_identifier(paper_id)
        normalized_limit = normalize_limit(limit, default=self._default_limit, maximum=100)
        normalized_pool = self._normalize_recommendation_pool(pool)
        cache_key = f"recommendations:{normalized_identifier}:{normalized_pool}:{normalized_limit}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, PaperCollectionResponse):
            return cached

        payload = await self._get_json(
            self._recommendations_client,
            f"/papers/forpaper/{quote(normalized_identifier, safe='')}",
            params={
                "from": normalized_pool,
                "limit": normalized_limit,
                "fields": self._RECOMMENDATION_FIELDS,
            },
        )
        result = PaperCollectionResponse(
            source="semantic_scholar",
            kind="recommended_papers",
            identifier=normalized_identifier,
            limit=normalized_limit,
            items=[
                normalize_semantic_scholar_paper(item)
                for item in payload.get("recommendedPapers") or []
            ],
        )
        self._cache_papers(result.items)
        self._cache.set(cache_key, result)
        return result

    async def recommend_from_examples(
        self,
        positive_paper_ids: list[str],
        negative_paper_ids: list[str] | None = None,
        *,
        limit: int | None = None,
    ) -> PaperCollectionResponse:
        normalized_positive_ids = self._normalize_identifier_list(
            positive_paper_ids,
            maximum=500,
        )
        normalized_negative_ids = self._normalize_identifier_list(
            negative_paper_ids or [],
            maximum=500,
            allow_empty=True,
        )
        normalized_limit = normalize_limit(limit, default=self._default_limit, maximum=100)
        cache_key = (
            "recommend_from_examples:"
            f"{','.join(normalized_positive_ids)}:{','.join(normalized_negative_ids)}:{normalized_limit}"
        )
        cached = self._cache.get(cache_key)
        if isinstance(cached, PaperCollectionResponse):
            return cached

        payload = await self._post_json(
            self._recommendations_client,
            "/papers/",
            params={
                "limit": normalized_limit,
                "fields": self._RECOMMENDATION_FIELDS,
            },
            json_body={
                "positivePaperIds": normalized_positive_ids,
                "negativePaperIds": normalized_negative_ids,
            },
        )
        result = PaperCollectionResponse(
            source="semantic_scholar",
            kind="recommend_from_examples",
            identifier=",".join(normalized_positive_ids),
            limit=normalized_limit,
            items=[
                normalize_semantic_scholar_paper(item)
                for item in payload.get("recommendedPapers") or []
            ],
        )
        self._cache_papers(result.items)
        self._cache.set(cache_key, result)
        return result

    async def _get_relation_collection(
        self,
        *,
        kind: str,
        paper_id: str,
        relation_path: str,
        relation_key: str,
        limit: int | None,
        offset: int | None,
    ) -> PaperCollectionResponse:
        normalized_identifier = await self._resolve_relation_identifier(paper_id)
        normalized_limit = normalize_limit(limit, default=self._default_limit, maximum=100)
        normalized_offset = normalize_offset(offset)
        cache_key = f"{kind}:{normalized_identifier}:{normalized_limit}:{normalized_offset}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, PaperCollectionResponse):
            return cached

        payload = await self._get_json(
            self._graph_client,
            f"/paper/{quote(normalized_identifier, safe='')}/{relation_path}",
            params={
                "limit": normalized_limit,
                "offset": normalized_offset,
                "fields": self._RELATION_FIELDS,
            },
        )

        items = []
        for edge in payload.get("data") or []:
            raw_paper = edge.get(relation_key) or {}
            if not raw_paper:
                continue
            items.append(
                normalize_semantic_scholar_paper(
                    raw_paper,
                    extra_metadata={
                        "contexts": edge.get("contexts") or [],
                        "intents": edge.get("intents") or [],
                        "is_influential_edge": edge.get("isInfluential"),
                    },
                )
            )

        result = PaperCollectionResponse(
            source="semantic_scholar",
            kind=kind,
            identifier=normalized_identifier,
            limit=normalized_limit,
            offset=payload.get("offset", normalized_offset),
            next_offset=payload.get("next"),
            items=items,
        )
        self._cache_papers(result.items)
        self._cache.set(cache_key, result)
        return result

    async def _get_json(
        self,
        client: httpx.AsyncClient,
        path: str,
        *,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        payload = await self._request_json(
            client,
            "GET",
            path,
            params=params,
        )
        if not isinstance(payload, dict):
            raise RuntimeError("Semantic Scholar returned an unexpected response payload.")

        return payload

    async def _post_json(
        self,
        client: httpx.AsyncClient,
        path: str,
        *,
        params: dict[str, Any],
        json_body: dict[str, Any],
    ) -> Any:
        return await self._request_json(
            client,
            "POST",
            path,
            params=params,
            json_body=json_body,
        )

    async def _request_json(
        self,
        client: httpx.AsyncClient,
        method: str,
        path: str,
        *,
        params: dict[str, Any],
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        # Semantic Scholar applies 1 RPS cumulatively across endpoints for API-key traffic,
        # so Graph and Recommendations requests share the same serialized gate.
        async with self._request_lock:
            for attempt in range(self._max_retry_attempts + 1):
                wait_seconds = self._minimum_interval_seconds - (
                    time.monotonic() - self._last_request_started_at
                )
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds + self._get_jitter_seconds())

                self._last_request_started_at = time.monotonic()

                try:
                    response = await client.request(
                        method,
                        path,
                        params=params,
                        json=json_body,
                    )
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError as exc:
                    if self._should_retry(exc.response, attempt):
                        retry_delay_seconds = self._get_retry_delay_seconds(
                            exc.response,
                            attempt,
                        )
                        LOGGER.warning(
                            "Retrying Semantic Scholar request after HTTP %s in %.2fs (%s %s, attempt %s/%s)",
                            exc.response.status_code,
                            retry_delay_seconds,
                            method,
                            path,
                            attempt + 1,
                            self._max_retry_attempts,
                        )
                        if retry_delay_seconds > 0:
                            await asyncio.sleep(retry_delay_seconds)
                        continue
                    raise RuntimeError(self._format_http_error(exc)) from exc
                except httpx.HTTPError as exc:
                    raise RuntimeError(f"Semantic Scholar request failed: {exc}") from exc

        raise RuntimeError("Semantic Scholar request failed after exhausting retries.")

    async def _resolve_relation_identifier(self, paper_id: str) -> str:
        normalized_identifier = self._normalize_identifier(paper_id)
        if self._SEMANTIC_SCHOLAR_PAPER_ID_PATTERN.fullmatch(normalized_identifier):
            return normalized_identifier

        paper = await self.get_paper(normalized_identifier)
        resolved_identifier = self._normalize_identifier(paper.source_id)
        if not self._SEMANTIC_SCHOLAR_PAPER_ID_PATTERN.fullmatch(resolved_identifier):
            raise RuntimeError(
                "Semantic Scholar did not return a canonical paperId for relation lookup."
            )
        return resolved_identifier

    def _cache_papers(self, papers: list[Paper]) -> None:
        for paper in papers:
            if paper.source != "semantic_scholar":
                continue
            normalized_identifier = self._normalize_simple_identifier(
                paper.source_id,
                label="paper_id",
            )
            self._cache.set(f"paper:{normalized_identifier}", paper)

    def _should_retry(self, response: httpx.Response, attempt: int) -> bool:
        return (
            response.status_code in {408, 429, 500, 502, 503, 504}
            and attempt < self._max_retry_attempts
        )

    def _get_retry_delay_seconds(self, response: httpx.Response, attempt: int) -> float:
        retry_after_seconds = self._parse_retry_after_seconds(
            response.headers.get("Retry-After")
        )
        if retry_after_seconds is not None:
            return retry_after_seconds + self._get_jitter_seconds()

        return min(
            self._max_retry_delay_seconds,
            self._initial_retry_delay_seconds * float(2**attempt),
        ) + self._get_jitter_seconds()

    def _get_jitter_seconds(self) -> float:
        if self._jitter_max_seconds <= 0:
            return 0.0
        return random.uniform(0.0, self._jitter_max_seconds)

    @staticmethod
    def _parse_retry_after_seconds(retry_after_value: str | None) -> float | None:
        if retry_after_value is None:
            return None

        normalized_value = retry_after_value.strip()
        if not normalized_value:
            return None

        try:
            return max(float(normalized_value), 0.0)
        except ValueError:
            pass

        try:
            retry_after_datetime = parsedate_to_datetime(normalized_value)
        except (TypeError, ValueError, IndexError):
            return None

        if retry_after_datetime is None:
            return None
        if retry_after_datetime.tzinfo is None:
            retry_after_datetime = retry_after_datetime.replace(tzinfo=timezone.utc)

        return max(
            (retry_after_datetime - datetime.now(timezone.utc)).total_seconds(),
            0.0,
        )

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
    def _normalize_identifier_list(
        identifiers: list[str],
        *,
        maximum: int,
        allow_empty: bool = False,
    ) -> list[str]:
        normalized_identifiers: list[str] = []
        for identifier in identifiers:
            normalized_identifier = SemanticScholarConnector._normalize_identifier(identifier)
            if normalized_identifier not in normalized_identifiers:
                normalized_identifiers.append(normalized_identifier)

        if not normalized_identifiers and not allow_empty:
            raise ValueError("At least one paper identifier is required.")
        if len(normalized_identifiers) > maximum:
            raise ValueError(f"No more than {maximum} paper identifiers are supported.")

        return normalized_identifiers

    @staticmethod
    def _normalize_simple_identifier(identifier: str, *, label: str) -> str:
        normalized_identifier = identifier.strip()
        if not normalized_identifier:
            raise ValueError(f"{label} must not be empty.")
        return normalized_identifier

    @staticmethod
    def _normalize_recommendation_pool(pool: str) -> str:
        normalized_pool = pool.strip().lower()
        if normalized_pool not in {"recent", "all-cs"}:
            raise ValueError("pool must be either 'recent' or 'all-cs'.")
        return normalized_pool

    @staticmethod
    def _format_http_error(exc: httpx.HTTPStatusError) -> str:
        response = exc.response
        detail: str | None = None
        retry_after = response.headers.get("Retry-After")
        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = str(payload.get("error") or payload.get("message") or "").strip() or None
        except ValueError:
            detail = None

        base_message = f"Semantic Scholar returned HTTP {response.status_code}."
        if retry_after:
            base_message = f"{base_message} Retry-After: {retry_after}."
        if detail:
            return f"{base_message} {detail}"
        return base_message
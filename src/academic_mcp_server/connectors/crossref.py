from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote

import httpx

from academic_mcp_server.common.cache import TTLCache
from academic_mcp_server.common.config import AppConfig
from academic_mcp_server.common.models import Paper, PaperCollectionResponse, PaperSearchResponse
from academic_mcp_server.common.normalize import normalize_crossref_reference, normalize_crossref_work, normalize_limit, normalize_offset


class CrossrefConnector:
    """Async client for Crossref REST API."""

    _SELECT_FIELDS = (
        "DOI,title,author,published-print,published-online,issued,created,indexed,deposited,"
        "container-title,abstract,URL,is-referenced-by-count,subject,publisher,type,"
        "license,link,relation,funder,ISSN"
    )
    def __init__(self, config: AppConfig) -> None:
        self._default_limit = config.default_limit
        self._contact_email = config.contact_email
        self._cache: TTLCache[Any] = TTLCache(config.cache_ttl_seconds)
        self._retryable_status_codes = {429, 503}
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

    async def get_work_references(
        self,
        doi: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> PaperCollectionResponse:
        normalized_doi = doi.strip()
        if not normalized_doi:
            raise ValueError("doi must not be empty.")

        normalized_limit = normalize_limit(limit, default=self._default_limit, maximum=100)
        normalized_offset = normalize_offset(offset)
        cache_key = f"work_references:{normalized_doi.lower()}:{normalized_limit}:{normalized_offset}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, PaperCollectionResponse):
            return cached

        message = await self._get_message(
            f"/works/{quote(normalized_doi, safe='')}",
            params={"mailto": self._contact_email},
        )
        references = [
            item for item in (message.get("reference") or []) if isinstance(item, dict)
        ]
        paged_references = references[
            normalized_offset : normalized_offset + normalized_limit
        ]
        next_offset = normalized_offset + len(paged_references)
        if next_offset >= len(references):
            next_offset = None

        result = PaperCollectionResponse(
            source="crossref",
            kind="work_references",
            identifier=normalized_doi,
            limit=normalized_limit,
            offset=normalized_offset,
            next_offset=next_offset,
            total=len(references),
            items=[normalize_crossref_reference(item) for item in paged_references],
        )
        self._cache.set(cache_key, result)
        return result

    async def get_journal_works(
        self,
        issn: str,
        *,
        limit: int | None = None,
        query: str | None = None,
    ) -> PaperCollectionResponse:
        normalized_issn = self._normalize_identifier(issn, label="issn")
        return await self._search_collection(
            path=f"/journals/{quote(normalized_issn, safe='')}/works",
            kind="journal_works",
            identifier=normalized_issn,
            limit=limit,
            query=query,
        )

    async def get_funder_works(
        self,
        funder_id: str,
        *,
        limit: int | None = None,
        query: str | None = None,
    ) -> PaperCollectionResponse:
        normalized_funder_id = self._normalize_identifier(funder_id, label="funder_id")
        return await self._search_collection(
            path=f"/funders/{quote(normalized_funder_id, safe='')}/works",
            kind="funder_works",
            identifier=normalized_funder_id,
            limit=limit,
            query=query,
        )

    async def get_type_works(
        self,
        type_id: str,
        *,
        limit: int | None = None,
        query: str | None = None,
    ) -> PaperCollectionResponse:
        normalized_type_id = self._normalize_identifier(type_id, label="type_id")
        return await self._search_collection(
            path=f"/types/{quote(normalized_type_id, safe='')}/works",
            kind="type_works",
            identifier=normalized_type_id,
            limit=limit,
            query=query,
        )

    async def _search_collection(
        self,
        *,
        path: str,
        kind: str,
        identifier: str,
        limit: int | None,
        query: str | None,
    ) -> PaperCollectionResponse:
        normalized_limit = normalize_limit(limit, default=self._default_limit, maximum=20)
        normalized_query = query.strip() if query else None
        cache_key = f"{kind}:{identifier}:{normalized_query or ''}:{normalized_limit}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, PaperCollectionResponse):
            return cached

        params: dict[str, Any] = {
            "rows": normalized_limit,
            "select": self._SELECT_FIELDS,
            "mailto": self._contact_email,
        }
        if normalized_query:
            params["query"] = normalized_query

        message = await self._get_message(path, params=params)
        result = PaperCollectionResponse(
            source="crossref",
            kind=kind,
            query=normalized_query,
            identifier=identifier,
            limit=normalized_limit,
            total=message.get("total-results"),
            items=[normalize_crossref_work(item) for item in message.get("items") or []],
        )
        self._cache.set(cache_key, result)
        return result

    async def _get_message(self, path: str, *, params: dict[str, Any]) -> dict[str, Any]:
        backoff_seconds = 1.0
        for attempt in range(3):
            try:
                response = await self._client.get(path, params=params)
                response.raise_for_status()
                payload = response.json()
                return payload.get("message") or {}
            except httpx.HTTPStatusError as exc:
                if (
                    exc.response.status_code in self._retryable_status_codes
                    and attempt < 2
                ):
                    await asyncio.sleep(
                        self._get_retry_delay_seconds(
                            exc.response,
                            default_seconds=backoff_seconds,
                        )
                    )
                    backoff_seconds *= 2
                    continue

                raise RuntimeError(self._format_http_error(exc)) from exc
            except httpx.HTTPError as exc:
                raise RuntimeError(f"Crossref request failed: {exc}") from exc

        raise RuntimeError("Crossref request retry loop exited unexpectedly.")

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

    @staticmethod
    def _get_retry_delay_seconds(
        response: httpx.Response,
        *,
        default_seconds: float,
    ) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after is None:
            return default_seconds

        normalized_retry_after = retry_after.strip()
        if normalized_retry_after.isdigit():
            return max(float(normalized_retry_after), 0.0)

        try:
            retry_at = parsedate_to_datetime(normalized_retry_after)
        except (TypeError, ValueError, IndexError, OverflowError):
            return default_seconds

        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)

        return max(
            (retry_at - datetime.now(timezone.utc)).total_seconds(),
            0.0,
        )

    @staticmethod
    def _normalize_identifier(identifier: str, *, label: str) -> str:
        normalized_identifier = identifier.strip()
        if not normalized_identifier:
            raise ValueError(f"{label} must not be empty.")
        return normalized_identifier
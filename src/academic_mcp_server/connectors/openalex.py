from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import quote

import httpx

from academic_mcp_server.common.cache import TTLCache
from academic_mcp_server.common.config import AppConfig
from academic_mcp_server.common.models import Paper, PaperCollectionResponse
from academic_mcp_server.common.normalize import normalize_limit, normalize_offset, normalize_openalex_work


class OpenAlexConnector:
    """Async client for OpenAlex works API used as a public citation fallback."""

    _SELECT_FIELDS = (
        "id,doi,title,display_name,publication_year,publication_date,updated_date,created_date,"
        "abstract_inverted_index,"
        "ids,authorships,primary_location,best_oa_location,open_access,cited_by_count,"
        "referenced_works_count,concepts,topics,counts_by_year,funders,type"
    )
    _REFERENCE_ID_FIELDS = "id,doi,referenced_works,referenced_works_count"
    _WORK_LOOKUP_CHUNK_SIZE = 25

    def __init__(self, config: AppConfig) -> None:
        self._default_limit = config.default_limit
        self._contact_email = config.openalex_contact_email
        self._cache: TTLCache[Any] = TTLCache(config.cache_ttl_seconds)
        self._retryable_status_codes = {408, 429, 500, 502, 503, 504}
        self._client = httpx.AsyncClient(
            base_url="https://api.openalex.org",
            headers=config.openalex_headers,
            timeout=config.request_timeout_seconds,
        )

    async def aclose(self) -> None:
        await self._client.aclose()
        self._cache.clear()

    async def get_work(self, identifier: str) -> Paper:
        normalized_identifier = identifier.strip()
        if not normalized_identifier:
            raise ValueError("identifier must not be empty.")

        cache_key = f"work:{normalized_identifier.lower()}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, Paper):
            return cached

        payload = await self._get_json(
            f"/works/{quote(self._normalize_work_identifier(normalized_identifier), safe=':/')}",
            params=self._request_params(),
        )
        result = normalize_openalex_work(payload)
        self._cache.set(cache_key, result)
        if result.doi:
            self._cache.set(f"work:{result.doi.lower()}", result)
        self._cache.set(f"work:{result.source_id.lower()}", result)
        return result

    async def get_references(
        self,
        identifier: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> PaperCollectionResponse:
        work = await self.get_work(identifier)
        normalized_limit = normalize_limit(limit, default=self._default_limit, maximum=100)
        normalized_offset = normalize_offset(offset)
        cache_key = f"references:{work.source_id}:{normalized_limit}:{normalized_offset}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, PaperCollectionResponse):
            return cached

        reference_ids = await self._get_reference_ids(identifier)
        paged_reference_ids = reference_ids[
            normalized_offset : normalized_offset + normalized_limit
        ]
        items = await self._get_works_by_ids(paged_reference_ids)
        consumed = normalized_offset + len(items)
        total = len(reference_ids)
        next_offset = consumed if consumed < total else None

        result = PaperCollectionResponse(
            source="openalex",
            kind="references",
            identifier=work.source_id,
            limit=normalized_limit,
            offset=normalized_offset,
            next_offset=next_offset,
            total=total,
            items=items,
        )
        self._cache.set(cache_key, result)
        return result

    async def get_citations(
        self,
        identifier: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> PaperCollectionResponse:
        work = await self.get_work(identifier)
        openalex_id = work.source_id
        normalized_limit = normalize_limit(limit, default=self._default_limit, maximum=100)
        normalized_offset = normalize_offset(offset)
        cache_key = f"citations:{openalex_id}:{normalized_limit}:{normalized_offset}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, PaperCollectionResponse):
            return cached

        page_size = min(normalized_limit, 100)
        page = (normalized_offset // page_size) + 1
        skip_on_first_page = normalized_offset % page_size
        collected: list[Paper] = []
        total: int | None = None
        next_offset: int | None = None

        while len(collected) < normalized_limit:
            payload = await self._get_json(
                "/works",
                params=self._request_params(
                    **{
                        "filter": f"cites:{openalex_id}",
                        "per-page": page_size,
                        "page": page,
                        "select": self._SELECT_FIELDS,
                    }
                ),
            )
            meta = payload.get("meta") or {}
            if meta.get("count") is not None:
                total = int(meta["count"])
            raw_items = payload.get("results") or []
            if not raw_items:
                break

            page_items = [
                normalize_openalex_work(item)
                for item in raw_items
                if isinstance(item, dict)
            ]
            if skip_on_first_page:
                page_items = page_items[skip_on_first_page:]
                skip_on_first_page = 0

            remaining = normalized_limit - len(collected)
            collected.extend(page_items[:remaining])
            if len(raw_items) < page_size:
                break
            page += 1

        consumed = normalized_offset + len(collected)
        if total is not None and consumed < total:
            next_offset = consumed

        result = PaperCollectionResponse(
            source="openalex",
            kind="citations",
            identifier=openalex_id,
            limit=normalized_limit,
            offset=normalized_offset,
            next_offset=next_offset,
            total=total,
            items=collected,
        )
        self._cache.set(cache_key, result)
        return result

    def _normalize_work_identifier(self, identifier: str) -> str:
        if identifier.startswith("https://openalex.org/"):
            return identifier
        return (
            f"https://doi.org/{identifier.removeprefix('https://doi.org/').removeprefix('http://doi.org/')}"
        )

    def _request_params(self, **params: Any) -> dict[str, Any]:
        request_params = {"mailto": self._contact_email}
        request_params.update(params)
        return request_params

    async def _get_reference_ids(self, identifier: str) -> list[str]:
        normalized_identifier = identifier.strip()
        cache_key = f"reference_ids:{normalized_identifier.lower()}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, list) and all(isinstance(item, str) for item in cached):
            return list(cached)

        payload = await self._get_json(
            f"/works/{quote(self._normalize_work_identifier(normalized_identifier), safe=':/')}",
            params=self._request_params(select=self._REFERENCE_ID_FIELDS),
        )
        reference_ids = [
            reference_id
            for reference_id in (payload.get("referenced_works") or [])
            if isinstance(reference_id, str) and reference_id.startswith("https://openalex.org/")
        ]
        self._cache.set(cache_key, reference_ids)
        return reference_ids

    async def _get_works_by_ids(self, work_ids: list[str]) -> list[Paper]:
        if not work_ids:
            return []

        results_by_id: dict[str, Paper] = {}
        for start in range(0, len(work_ids), self._WORK_LOOKUP_CHUNK_SIZE):
            chunk = work_ids[start : start + self._WORK_LOOKUP_CHUNK_SIZE]
            payload = await self._get_json(
                "/works",
                params=self._request_params(
                    **{
                        "filter": f"openalex:{'|'.join(chunk)}",
                        "per-page": len(chunk),
                        "select": self._SELECT_FIELDS,
                    }
                ),
            )
            for item in payload.get("results") or []:
                if not isinstance(item, dict):
                    continue
                paper = normalize_openalex_work(item)
                results_by_id[paper.source_id] = paper
                self._cache.set(f"work:{paper.source_id.lower()}", paper)
                if paper.doi:
                    self._cache.set(f"work:{paper.doi.lower()}", paper)

        return [results_by_id[work_id] for work_id in work_ids if work_id in results_by_id]

    async def _get_json(self, path: str, *, params: dict[str, Any]) -> dict[str, Any]:
        backoff_seconds = 1.0
        for attempt in range(4):
            try:
                response = await self._client.get(path, params=params)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise RuntimeError("OpenAlex returned an unexpected response payload.")
                return payload
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in self._retryable_status_codes and attempt < 3:
                    await asyncio.sleep(backoff_seconds)
                    backoff_seconds *= 2
                    continue
                raise RuntimeError(self._format_http_error(exc)) from exc
            except httpx.HTTPError as exc:
                raise RuntimeError(f"OpenAlex request failed: {exc}") from exc

        raise RuntimeError("OpenAlex request retry loop exited unexpectedly.")

    @staticmethod
    def _format_http_error(exc: httpx.HTTPStatusError) -> str:
        response = exc.response
        detail: str | None = None
        try:
            payload = response.json()
            if isinstance(payload, dict):
                error = payload.get("error")
                if isinstance(error, str):
                    detail = error.strip() or None
        except Exception:
            detail = None
        message = f"OpenAlex request failed with HTTP {response.status_code}"
        if detail:
            return f"{message}: {detail}"
        return message
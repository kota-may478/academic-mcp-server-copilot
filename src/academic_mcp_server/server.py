from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, cast

from mcp.server.fastmcp import Context, FastMCP

from academic_mcp_server.common.config import AppConfig
from academic_mcp_server.common.models import Paper, PaperCollectionResponse, SUPPORTED_SOURCES, PaperSource, SourceError, UnifiedSearchResponse
from academic_mcp_server.common.normalize import normalize_limit, sort_papers_for_display
from academic_mcp_server.connectors import ArxivConnector, CrossrefConnector, OpenAlexConnector, SemanticScholarConnector


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ServerRuntime:
    config: AppConfig
    semantic_scholar: SemanticScholarConnector
    arxiv: ArxivConnector
    crossref: CrossrefConnector
    openalex: OpenAlexConnector

    async def aclose(self) -> None:
        await asyncio.gather(
            self.semantic_scholar.aclose(),
            self.arxiv.aclose(),
            self.crossref.aclose(),
            self.openalex.aclose(),
        )


@asynccontextmanager
async def server_lifespan(_: FastMCP) -> AsyncIterator[ServerRuntime]:
    config = AppConfig.from_env()
    config_state_message = (
        "Starting academicPaperSearch with config state: "
        f"semantic_scholar_api_key={'present' if config.semantic_scholar_api_key else 'absent'}, "
        f"contact_email={'present' if config.contact_email else 'absent'}"
    )
    LOGGER.info(config_state_message)
    print(config_state_message, file=sys.stderr, flush=True)
    runtime = ServerRuntime(
        config=config,
        semantic_scholar=SemanticScholarConnector(config),
        arxiv=ArxivConnector(config),
        crossref=CrossrefConnector(config),
        openalex=OpenAlexConnector(config),
    )
    try:
        yield runtime
    finally:
        await runtime.aclose()


mcp = FastMCP(
    name="academicPaperSearch",
    instructions=(
        "Search academic papers across Semantic Scholar, arXiv, and Crossref. "
        "Use search_papers for quick normalized cross-source discovery, then use the "
        "source-specific tools for exact paper lookup, citations, references, author "
        "profiles, recommendations, arXiv full-text analysis, and Crossref journal, "
        "funder, or type slices."
    ),
    lifespan=server_lifespan,
    log_level="INFO",
)


def build_server() -> FastMCP:
    return mcp


def _get_runtime(ctx: Context) -> ServerRuntime:
    runtime = ctx.request_context.lifespan_context
    if not isinstance(runtime, ServerRuntime):
        raise RuntimeError("Server runtime is unavailable.")
    return runtime


def _require_context(ctx: Context | None) -> Context:
    if ctx is None:
        raise RuntimeError("Tool context is unavailable.")
    return ctx


def _normalize_sources(sources: list[str] | None) -> list[PaperSource]:
    if not sources:
        return list(SUPPORTED_SOURCES)

    normalized_sources: list[PaperSource] = []
    for source in sources:
        if source not in SUPPORTED_SOURCES:
            supported = ", ".join(SUPPORTED_SOURCES)
            raise ValueError(f"Unsupported source '{source}'. Supported sources: {supported}.")
        typed_source = cast(PaperSource, source)
        if typed_source not in normalized_sources:
            normalized_sources.append(typed_source)

    return normalized_sources


def _normalize_recommendation_pool(pool: str) -> str:
    normalized_pool = pool.strip().lower()
    if normalized_pool not in {"recent", "all-cs"}:
        raise ValueError("pool must be either 'recent' or 'all-cs'.")
    return normalized_pool


def _should_fallback_to_crossref_references(paper: Paper) -> bool:
    return bool(paper.doi and (paper.reference_count or 0) > 0)


def _extract_doi_candidate(identifier: str) -> str | None:
    normalized = identifier.strip()
    if not normalized:
        return None
    if normalized.lower().startswith("https://doi.org/"):
        normalized = normalized[16:]
    elif normalized.lower().startswith("http://doi.org/"):
        normalized = normalized[15:]
    if "/" not in normalized or " " in normalized:
        return None
    return normalized


async def _resolve_paper_and_doi(
    runtime: ServerRuntime,
    *,
    paper_id: str,
) -> tuple[Paper | None, str | None]:
    doi = _extract_doi_candidate(paper_id)
    semantic_scholar_paper: Paper | None = None
    if doi is not None:
        return None, doi

    try:
        semantic_scholar_paper = await runtime.semantic_scholar.get_paper(paper_id=paper_id)
    except Exception:
        return None, None

    return semantic_scholar_paper, semantic_scholar_paper.doi


async def _get_semantic_scholar_references_with_fallback(
    runtime: ServerRuntime,
    *,
    paper_id: str,
    limit: int,
    offset: int,
    ctx: Context,
) -> PaperCollectionResponse:
    semantic_scholar_paper, doi = await _resolve_paper_and_doi(
        runtime,
        paper_id=paper_id,
    )
    if doi:
        try:
            openalex_result = await runtime.openalex.get_references(
                identifier=doi,
                limit=limit,
                offset=offset,
            )
            if openalex_result.items:
                ctx.info(
                    "OpenAlex primary provider for Semantic Scholar references",
                    paper_id=paper_id,
                    doi=doi,
                    openalex_items=len(openalex_result.items),
                )
                return PaperCollectionResponse(
                    source="semantic_scholar",
                    kind="references",
                    identifier=(
                        semantic_scholar_paper.source_id
                        if semantic_scholar_paper
                        else openalex_result.identifier
                    ),
                    limit=openalex_result.limit,
                    offset=openalex_result.offset,
                    next_offset=openalex_result.next_offset,
                    total=openalex_result.total,
                    items=openalex_result.items,
                )
        except Exception as exc:
            ctx.info(
                "OpenAlex references provider failed; falling back to Semantic Scholar",
                paper_id=paper_id,
                doi=doi,
                openalex_error=str(exc),
            )

    result = await runtime.semantic_scholar.get_references(
        paper_id=paper_id,
        limit=limit,
        offset=offset,
    )
    if result.items:
        return result

    paper = semantic_scholar_paper or await runtime.semantic_scholar.get_paper(paper_id=paper_id)
    if not _should_fallback_to_crossref_references(paper):
        return result

    fallback = await runtime.crossref.get_work_references(
        doi=paper.doi,
        limit=limit,
        offset=offset,
    )
    if not fallback.items:
        return result

    ctx.info(
        "Crossref fallback for Semantic Scholar references",
        paper_id=paper.source_id,
        doi=paper.doi,
        semantic_scholar_reference_count=paper.reference_count,
        fallback_items=len(fallback.items),
    )
    return PaperCollectionResponse(
        source="semantic_scholar",
        kind="references",
        identifier=result.identifier or paper.source_id,
        limit=result.limit,
        offset=result.offset,
        next_offset=fallback.next_offset,
        total=fallback.total or paper.reference_count,
        items=fallback.items,
    )


async def _get_openalex_citations_fallback(
    runtime: ServerRuntime,
    *,
    paper_id: str,
    limit: int,
    offset: int,
    ctx: Context,
    semantic_scholar_error: Exception | None = None,
) -> PaperCollectionResponse | None:
    semantic_scholar_paper, doi = await _resolve_paper_and_doi(
        runtime,
        paper_id=paper_id,
    )

    if not doi:
        return None

    fallback = await runtime.openalex.get_citations(
        identifier=doi,
        limit=limit,
        offset=offset,
    )
    if not fallback.items:
        return None

    ctx.info(
        "OpenAlex primary provider for Semantic Scholar citations",
        paper_id=paper_id,
        doi=doi,
        openalex_items=len(fallback.items),
        semantic_scholar_error=str(semantic_scholar_error) if semantic_scholar_error else None,
    )
    return PaperCollectionResponse(
        source="semantic_scholar",
        kind="citations",
        identifier=(semantic_scholar_paper.source_id if semantic_scholar_paper else fallback.identifier),
        limit=fallback.limit,
        offset=fallback.offset,
        next_offset=fallback.next_offset,
        total=fallback.total,
        items=fallback.items,
    )


async def _get_semantic_scholar_citations_with_fallback(
    runtime: ServerRuntime,
    *,
    paper_id: str,
    limit: int,
    offset: int,
    ctx: Context,
) -> PaperCollectionResponse:
    openalex_result = await _get_openalex_citations_fallback(
        runtime,
        paper_id=paper_id,
        limit=limit,
        offset=offset,
        ctx=ctx,
    )
    if openalex_result is not None:
        return openalex_result

    semantic_scholar_error: Exception | None = None
    try:
        result = await runtime.semantic_scholar.get_citations(
            paper_id=paper_id,
            limit=limit,
            offset=offset,
        )
        if result.items:
            return result
    except Exception as exc:
        semantic_scholar_error = exc
        result = PaperCollectionResponse(
            source="semantic_scholar",
            kind="citations",
            identifier=paper_id,
            limit=limit,
            offset=offset,
            items=[],
        )

    if semantic_scholar_error is not None:
        raise semantic_scholar_error
    return result


@mcp.tool(
    name="semantic_scholar_search",
    description="Search Semantic Scholar papers by keyword query.",
)
async def semantic_scholar_search(query: str, limit: int = 10, ctx: Context | None = None) -> dict[str, Any]:
    ctx = _require_context(ctx)
    runtime = _get_runtime(ctx)
    ctx.info("Semantic Scholar search", query=query, limit=limit)
    result = await runtime.semantic_scholar.search(query=query, limit=limit)
    return result.model_dump(mode="json")


@mcp.tool(
    name="semantic_scholar_paper",
    description="Fetch a single Semantic Scholar paper by paper ID, DOI, or other supported identifier.",
)
async def semantic_scholar_paper(paper_id: str, ctx: Context | None = None) -> dict[str, Any]:
    ctx = _require_context(ctx)
    runtime = _get_runtime(ctx)
    ctx.info("Semantic Scholar paper lookup", paper_id=paper_id)
    result = await runtime.semantic_scholar.get_paper(paper_id=paper_id)
    return result.model_dump(mode="json")


@mcp.tool(
    name="semantic_scholar_paper_batch",
    description="Fetch multiple Semantic Scholar papers in one batch by paper IDs, DOI IDs, or other supported identifiers.",
)
async def semantic_scholar_paper_batch(
    paper_ids: list[str],
    ctx: Context | None = None,
) -> dict[str, Any]:
    ctx = _require_context(ctx)
    runtime = _get_runtime(ctx)
    ctx.info("Semantic Scholar paper batch lookup", count=len(paper_ids))
    result = await runtime.semantic_scholar.get_papers_batch(paper_ids=paper_ids)
    return result.model_dump(mode="json")


@mcp.tool(
    name="semantic_scholar_citations",
    description="Fetch papers that cite a Semantic Scholar paper.",
)
async def semantic_scholar_citations(
    paper_id: str,
    limit: int = 10,
    offset: int = 0,
    ctx: Context | None = None,
) -> dict[str, Any]:
    ctx = _require_context(ctx)
    runtime = _get_runtime(ctx)
    ctx.info("Semantic Scholar citations lookup", paper_id=paper_id, limit=limit, offset=offset)
    result = await _get_semantic_scholar_citations_with_fallback(
        runtime,
        paper_id=paper_id,
        limit=limit,
        offset=offset,
        ctx=ctx,
    )
    return result.model_dump(mode="json")


@mcp.tool(
    name="semantic_scholar_references",
    description="Fetch papers referenced by a Semantic Scholar paper.",
)
async def semantic_scholar_references(
    paper_id: str,
    limit: int = 10,
    offset: int = 0,
    ctx: Context | None = None,
) -> dict[str, Any]:
    ctx = _require_context(ctx)
    runtime = _get_runtime(ctx)
    ctx.info("Semantic Scholar references lookup", paper_id=paper_id, limit=limit, offset=offset)
    result = await _get_semantic_scholar_references_with_fallback(
        runtime,
        paper_id=paper_id,
        limit=limit,
        offset=offset,
        ctx=ctx,
    )
    return result.model_dump(mode="json")


@mcp.tool(
    name="semantic_scholar_author_search",
    description="Search Semantic Scholar authors by name.",
)
async def semantic_scholar_author_search(
    query: str,
    limit: int = 10,
    offset: int = 0,
    ctx: Context | None = None,
) -> dict[str, Any]:
    ctx = _require_context(ctx)
    runtime = _get_runtime(ctx)
    ctx.info("Semantic Scholar author search", query=query, limit=limit, offset=offset)
    result = await runtime.semantic_scholar.search_authors(
        query=query,
        limit=limit,
        offset=offset,
    )
    return result.model_dump(mode="json")


@mcp.tool(
    name="semantic_scholar_author",
    description="Fetch a single Semantic Scholar author by author ID.",
)
async def semantic_scholar_author(author_id: str, ctx: Context | None = None) -> dict[str, Any]:
    ctx = _require_context(ctx)
    runtime = _get_runtime(ctx)
    ctx.info("Semantic Scholar author lookup", author_id=author_id)
    result = await runtime.semantic_scholar.get_author(author_id=author_id)
    return result.model_dump(mode="json")


@mcp.tool(
    name="semantic_scholar_author_papers",
    description="Fetch papers for a Semantic Scholar author.",
)
async def semantic_scholar_author_papers(
    author_id: str,
    limit: int = 10,
    offset: int = 0,
    ctx: Context | None = None,
) -> dict[str, Any]:
    ctx = _require_context(ctx)
    runtime = _get_runtime(ctx)
    ctx.info("Semantic Scholar author papers lookup", author_id=author_id, limit=limit, offset=offset)
    result = await runtime.semantic_scholar.get_author_papers(
        author_id=author_id,
        limit=limit,
        offset=offset,
    )
    return result.model_dump(mode="json")


@mcp.tool(
    name="semantic_scholar_recommended_papers",
    description="Fetch recommended papers for a single Semantic Scholar paper.",
)
async def semantic_scholar_recommended_papers(
    paper_id: str,
    limit: int = 10,
    pool: str = "recent",
    ctx: Context | None = None,
) -> dict[str, Any]:
    ctx = _require_context(ctx)
    runtime = _get_runtime(ctx)
    normalized_pool = _normalize_recommendation_pool(pool)
    ctx.info(
        "Semantic Scholar recommended papers lookup",
        paper_id=paper_id,
        limit=limit,
        pool=normalized_pool,
    )
    result = await runtime.semantic_scholar.get_recommended_papers(
        paper_id=paper_id,
        limit=limit,
        pool=normalized_pool,
    )
    return result.model_dump(mode="json")


@mcp.tool(
    name="semantic_scholar_recommend_from_examples",
    description="Fetch Semantic Scholar recommendations from positive and optional negative example papers.",
)
async def semantic_scholar_recommend_from_examples(
    positive_paper_ids: list[str],
    negative_paper_ids: list[str] | None = None,
    limit: int = 10,
    ctx: Context | None = None,
) -> dict[str, Any]:
    ctx = _require_context(ctx)
    runtime = _get_runtime(ctx)
    ctx.info(
        "Semantic Scholar example-based recommendations lookup",
        positive_count=len(positive_paper_ids),
        negative_count=len(negative_paper_ids or []),
        limit=limit,
    )
    result = await runtime.semantic_scholar.recommend_from_examples(
        positive_paper_ids=positive_paper_ids,
        negative_paper_ids=negative_paper_ids,
        limit=limit,
    )
    return result.model_dump(mode="json")


@mcp.tool(
    name="arxiv_search",
    description="Search arXiv papers and preprints through the Atom query API.",
)
async def arxiv_search(query: str, limit: int = 10, ctx: Context | None = None) -> dict[str, Any]:
    ctx = _require_context(ctx)
    runtime = _get_runtime(ctx)
    ctx.info("arXiv search", query=query, limit=limit)
    result = await runtime.arxiv.search(query=query, limit=limit)
    return result.model_dump(mode="json")


@mcp.tool(
    name="arxiv_paper",
    description="Fetch a single arXiv paper by arXiv ID or arXiv URL.",
)
async def arxiv_paper(arxiv_id: str, ctx: Context | None = None) -> dict[str, Any]:
    ctx = _require_context(ctx)
    runtime = _get_runtime(ctx)
    ctx.info("arXiv paper lookup", arxiv_id=arxiv_id)
    result = await runtime.arxiv.get_paper(arxiv_id=arxiv_id)
    return result.model_dump(mode="json")


@mcp.tool(
    name="arxiv_full_text",
    description=(
        "Download and analyze an arXiv paper's full text from source files or PDF. "
        "When source files are available, also extract figure and table captions. "
        "Set max_characters=0 to disable truncation."
    ),
)
async def arxiv_full_text(
    arxiv_id: str,
    prefer: str = "source",
    max_characters: int = 200000,
    ctx: Context | None = None,
) -> dict[str, Any]:
    ctx = _require_context(ctx)
    runtime = _get_runtime(ctx)
    ctx.info(
        "arXiv full text analysis",
        arxiv_id=arxiv_id,
        prefer=prefer,
        max_characters=max_characters,
    )
    result = await runtime.arxiv.analyze_full_text(
        arxiv_id=arxiv_id,
        prefer=prefer,
        max_characters=max_characters,
    )
    return result.model_dump(mode="json")


@mcp.tool(
    name="crossref_search_works",
    description="Search Crossref works metadata by free-text query.",
)
async def crossref_search_works(query: str, limit: int = 10, ctx: Context | None = None) -> dict[str, Any]:
    ctx = _require_context(ctx)
    runtime = _get_runtime(ctx)
    ctx.info("Crossref works search", query=query, limit=limit)
    result = await runtime.crossref.search_works(query=query, limit=limit)
    return result.model_dump(mode="json")


@mcp.tool(
    name="crossref_work_by_doi",
    description="Fetch one Crossref work by DOI.",
)
async def crossref_work_by_doi(doi: str, ctx: Context | None = None) -> dict[str, Any]:
    ctx = _require_context(ctx)
    runtime = _get_runtime(ctx)
    ctx.info("Crossref DOI lookup", doi=doi)
    result = await runtime.crossref.get_work_by_doi(doi=doi)
    return result.model_dump(mode="json")


@mcp.tool(
    name="crossref_journal_works",
    description="Fetch Crossref works for a journal ISSN, optionally narrowed by a query string.",
)
async def crossref_journal_works(
    issn: str,
    query: str | None = None,
    limit: int = 10,
    ctx: Context | None = None,
) -> dict[str, Any]:
    ctx = _require_context(ctx)
    runtime = _get_runtime(ctx)
    ctx.info("Crossref journal works lookup", issn=issn, query=query, limit=limit)
    result = await runtime.crossref.get_journal_works(
        issn=issn,
        query=query,
        limit=limit,
    )
    return result.model_dump(mode="json")


@mcp.tool(
    name="crossref_funder_works",
    description="Fetch Crossref works for a funder ID, optionally narrowed by a query string.",
)
async def crossref_funder_works(
    funder_id: str,
    query: str | None = None,
    limit: int = 10,
    ctx: Context | None = None,
) -> dict[str, Any]:
    ctx = _require_context(ctx)
    runtime = _get_runtime(ctx)
    ctx.info("Crossref funder works lookup", funder_id=funder_id, query=query, limit=limit)
    result = await runtime.crossref.get_funder_works(
        funder_id=funder_id,
        query=query,
        limit=limit,
    )
    return result.model_dump(mode="json")


@mcp.tool(
    name="crossref_type_works",
    description="Fetch Crossref works for a Crossref work type, optionally narrowed by a query string.",
)
async def crossref_type_works(
    type_id: str,
    query: str | None = None,
    limit: int = 10,
    ctx: Context | None = None,
) -> dict[str, Any]:
    ctx = _require_context(ctx)
    runtime = _get_runtime(ctx)
    ctx.info("Crossref type works lookup", type_id=type_id, query=query, limit=limit)
    result = await runtime.crossref.get_type_works(
        type_id=type_id,
        query=query,
        limit=limit,
    )
    return result.model_dump(mode="json")


@mcp.tool(
    name="search_papers",
    description="Search across Semantic Scholar, arXiv, and Crossref with normalized output.",
)
async def search_papers(
    query: str,
    sources: list[str] | None = None,
    limit_per_source: int = 5,
    ctx: Context | None = None,
) -> dict[str, Any]:
    ctx = _require_context(ctx)
    runtime = _get_runtime(ctx)
    selected_sources = _normalize_sources(sources)
    normalized_limit = normalize_limit(
        limit_per_source,
        default=runtime.config.default_limit,
        maximum=20,
    )
    ctx.info(
        "Unified paper search",
        query=query,
        sources=selected_sources,
        limit_per_source=normalized_limit,
    )

    requests: dict[PaperSource, asyncio.Future[Any] | Any] = {}
    if "semantic_scholar" in selected_sources:
        requests["semantic_scholar"] = runtime.semantic_scholar.search(
            query=query,
            limit=normalized_limit,
        )
    if "arxiv" in selected_sources:
        requests["arxiv"] = runtime.arxiv.search(query=query, limit=normalized_limit)
    if "crossref" in selected_sources:
        requests["crossref"] = runtime.crossref.search_works(
            query=query,
            limit=normalized_limit,
        )

    results = await asyncio.gather(*requests.values(), return_exceptions=True)

    merged_items = []
    errors: list[SourceError] = []
    for source, result in zip(requests.keys(), results, strict=True):
        if isinstance(result, Exception):
            errors.append(SourceError(source=source, message=str(result)))
            continue
        merged_items.extend(result.items)

    response = UnifiedSearchResponse(
        query=query.strip(),
        sources=selected_sources,
        limit_per_source=normalized_limit,
        items=sort_papers_for_display(merged_items),
        errors=errors,
    )
    return response.model_dump(mode="json")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
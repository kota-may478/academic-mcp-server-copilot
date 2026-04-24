from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, cast

from mcp.server.fastmcp import Context, FastMCP

from academic_mcp_server.common.config import AppConfig
from academic_mcp_server.common.models import SUPPORTED_SOURCES, PaperSource, SourceError, UnifiedSearchResponse
from academic_mcp_server.common.normalize import normalize_limit, sort_papers_for_display
from academic_mcp_server.connectors import ArxivConnector, CrossrefConnector, SemanticScholarConnector


@dataclass(slots=True)
class ServerRuntime:
    config: AppConfig
    semantic_scholar: SemanticScholarConnector
    arxiv: ArxivConnector
    crossref: CrossrefConnector

    async def aclose(self) -> None:
        await asyncio.gather(
            self.semantic_scholar.aclose(),
            self.arxiv.aclose(),
            self.crossref.aclose(),
        )


@asynccontextmanager
async def server_lifespan(_: FastMCP) -> AsyncIterator[ServerRuntime]:
    config = AppConfig.from_env()
    runtime = ServerRuntime(
        config=config,
        semantic_scholar=SemanticScholarConnector(config),
        arxiv=ArxivConnector(config),
        crossref=CrossrefConnector(config),
    )
    try:
        yield runtime
    finally:
        await runtime.aclose()


mcp = FastMCP(
    name="academicPaperSearch",
    instructions=(
        "Search academic papers across Semantic Scholar, arXiv, and Crossref. "
        "Use the source-specific tools when you need provider-specific behavior, "
        "or use search_papers for a normalized multi-source search."
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


@mcp.tool(
    name="semantic_scholar_search",
    description="Search Semantic Scholar papers by keyword query.",
)
async def semantic_scholar_search(query: str, limit: int = 10, ctx: Context = None) -> dict[str, Any]:
    runtime = _get_runtime(ctx)
    ctx.info("Semantic Scholar search", query=query, limit=limit)
    result = await runtime.semantic_scholar.search(query=query, limit=limit)
    return result.model_dump(mode="json")


@mcp.tool(
    name="semantic_scholar_paper",
    description="Fetch a single Semantic Scholar paper by paper ID, DOI, or other supported identifier.",
)
async def semantic_scholar_paper(paper_id: str, ctx: Context = None) -> dict[str, Any]:
    runtime = _get_runtime(ctx)
    ctx.info("Semantic Scholar paper lookup", paper_id=paper_id)
    result = await runtime.semantic_scholar.get_paper(paper_id=paper_id)
    return result.model_dump(mode="json")


@mcp.tool(
    name="arxiv_search",
    description="Search arXiv papers and preprints through the Atom query API.",
)
async def arxiv_search(query: str, limit: int = 10, ctx: Context = None) -> dict[str, Any]:
    runtime = _get_runtime(ctx)
    ctx.info("arXiv search", query=query, limit=limit)
    result = await runtime.arxiv.search(query=query, limit=limit)
    return result.model_dump(mode="json")


@mcp.tool(
    name="crossref_search_works",
    description="Search Crossref works metadata by free-text query.",
)
async def crossref_search_works(query: str, limit: int = 10, ctx: Context = None) -> dict[str, Any]:
    runtime = _get_runtime(ctx)
    ctx.info("Crossref works search", query=query, limit=limit)
    result = await runtime.crossref.search_works(query=query, limit=limit)
    return result.model_dump(mode="json")


@mcp.tool(
    name="crossref_work_by_doi",
    description="Fetch one Crossref work by DOI.",
)
async def crossref_work_by_doi(doi: str, ctx: Context = None) -> dict[str, Any]:
    runtime = _get_runtime(ctx)
    ctx.info("Crossref DOI lookup", doi=doi)
    result = await runtime.crossref.get_work_by_doi(doi=doi)
    return result.model_dump(mode="json")


@mcp.tool(
    name="search_papers",
    description="Search across Semantic Scholar, arXiv, and Crossref with normalized output.",
)
async def search_papers(
    query: str,
    sources: list[str] | None = None,
    limit_per_source: int = 5,
    ctx: Context = None,
) -> dict[str, Any]:
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